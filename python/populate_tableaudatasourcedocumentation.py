import logging
from elasticsearch_dsl import connections as es_connections
from datasearchtool.daemon.properties import (
    elasticsearch_defaults,
    mysql_connection_string,
    TABLEAU_PROJECTS_MAP,
)
from datasearchtool.models import configure_orm
from datasearchtool.doctype import (
    TableauDataSourceDocumentation,
    BloodmoonTableDocumentation,
)
from datasearchtool.common.datasets import get_databases_map
from datasearchtool.doctype import MySqlTableDocumentation
from datasearchtool.doctype.bloodmoontabledocumentation import BLOOD_MOON_DATABASE
from datasearchtool.doctype.tableaudatasourcedocumentation import (
    TableauDataSourceMetadataField,
    TableauDataSourceQueryField,
    TableauDataSourceInputSource,
    TableauDataSourceReport,
)
from datasearchtool.doctype.base import BaseDocType
from datasearchtool.doctype.certified import CERTIFICATION_FIELD_NAME
from datasearchtool.lib.gateway_builder import GatewayBuilder
from datasearchtool.lib.tableau.gateway import (
    TableauGateway,
    SETTINGS_MAP,
    REQUIRED_SETTINGS,
)
from datasearchtool.lib.tableau.data_source_parser import (
    TableauDataSourceParser,
    FIELD_NAME_KEY,
    FIELD_DATA_TYPE_KEY,
    FIELD_DESCRIPTION_KEY,
    FIELD_FORMULA_KEY,
    TOTAL_COUNT_KEY,
)
from datasearchtool.utils.elastic_search import (
    document_exists,
    synchronize_nested_list,
    create_elastic_search_objects,
)
from datasearchtool.common.tableau import build_tableau_projects_settings


# Workbook fields names on Tableau's metadata API
WORKBOOK_ID_KEY = "id"
WORKBOOK_LUID_KEY = "luid"
WORKBOOK_NAME_KEY = "name"
WORKBOOK_PROJECT_NAME_KEY = "projectName"
WORKBOOK_DESCRIPTION_KEY = "description"
WORKBOOK_URL_ID_KEY = "vizportalUrlId"
WORKBOOK_VIEWS_KEY = "viewsConnection"
WORKBOOK_SHEETS_KEY = "sheetsConnection"
WORKBOOK_OWNER_KEY = "owner"
WORKBOOK_OWNER_NAME_KEY = "name"
WORKBOOK_OWNER_USERNAME_KEY = "username"
WORKBOOK_OWNER_EMAIL_KEY = "email"


DOCUMENT_NAME_KEY = "name"
DOCUMENT_LUID_KEY = "luid"
DOCUMENT_CUSTOM_SQL_KEY = "custom_sql"
DOCUMENT_INPUT_SOURCES_KEY = "input_sources"
DOCUMENT_METADATA_FIELDS_KEY = "metadata_fields"
DOCUMENT_QUERY_FIELDS_KEY = "query_fields"
DOCUMENT_METADATA_FIELD_ID_KEY = "id"
DOCUMENT_METADATA_FIELD_NAME_KEY = "field"
DOCUMENT_METADATA_FIELD_DATA_TYPE_KEY = "data_type"
DOCUMENT_METADATA_FIELD_DEFINITION_KEY = "definition"
DOCUMENT_METADATA_FIELD_TRANSFORMATION_KEY = "transformation"
DOCUMENT_INPUT_SOURCE_TYPE_KEY = "data_source_type"
DOCUMENT_INPUT_SOURCE_NAME_KEY = "data_source_name"
DOCUMENT_INPUT_SOURCE_DATABASE_KEY = "database"
DOCUMENT_INPUT_SOURCE_DOC_TYPE_KEY = "doc_type"
DOCUMENT_INPUT_SOURCE_DOC_ID_KEY = "doc_id"
DOCUMENT_QUERY_FIELD_NAME_KEY = "field_name"
DOCUMENT_QUERY_FIELD_DATA_TYPE_KEY = "data_type"
DOCUMENT_QUERY_FIELD_DEFINITION_KEY = "definition"
DOCUMENT_REPORTS_KEY = "reports"
DOCUMENT_REPORTS_TOTAL_COUNT = "reports_total_count"
DOCUMENT_REPORT_ID_KEY = "id"
DOCUMENT_REPORT_LUID_KEY = "luid"
DOCUMENT_REPORT_NAME_KEY = "name"
DOCUMENT_REPORT_PROJECT_NAME_KEY = "project_name"
DOCUMENT_REPORT_DESCRIPTION_KEY = "description"
DOCUMENT_REPORT_URL_ID_KEY = "url_id"
DOCUMENT_REPORT_VIEWS_COUNT_KEY = "views_count"
DOCUMENT_REPORT_SHEETS_COUNT_KEY = "sheets_count"
DOCUMENT_REPORT_OWNER_NAME_KEY = "owner_name"
DOCUMENT_REPORT_OWNER_USERNAME_KEY = "owner_username"
DOCUMENT_REPORT_OWNER_EMAIL_KEY = "owner_username"


# Databases in this map will be imported
# If the database cannot be inferred, then use the default
# If the database can be inferred, but it is not on this map,
#   then it will not be imported
SQL_TABLE_DATA_SOURCE_TYPE = "SQL Table"
INPUT_SOURCE_DATABASE_DEFAULT = BLOOD_MOON_DATABASE
INPUT_SOURCE_DATA_SOURCE_TYPE_MAP = {BLOOD_MOON_DATABASE: SQL_TABLE_DATA_SOURCE_TYPE}

INPUT_SOURCE_DATA_SOURCE_NAME_SEPARATOR = "."


# Maps Tableau's naming to Alexandria' naming
METADATA_FIELDS_MAP = {
    FIELD_NAME_KEY: DOCUMENT_METADATA_FIELD_NAME_KEY,
    FIELD_DATA_TYPE_KEY: DOCUMENT_METADATA_FIELD_DATA_TYPE_KEY,
    FIELD_DESCRIPTION_KEY: DOCUMENT_METADATA_FIELD_DEFINITION_KEY,
    FIELD_FORMULA_KEY: DOCUMENT_METADATA_FIELD_TRANSFORMATION_KEY,
}

# Maps Tableau's naming to Alexandria' naming
QUERY_FIELDS_MAP = {
    FIELD_NAME_KEY: DOCUMENT_QUERY_FIELD_NAME_KEY,
    FIELD_DATA_TYPE_KEY: DOCUMENT_QUERY_FIELD_DATA_TYPE_KEY,
    FIELD_DESCRIPTION_KEY: DOCUMENT_QUERY_FIELD_DEFINITION_KEY,
}

# Maps Tableau's naming to Alexandria' naming
REPORTS_MAP = {
    WORKBOOK_ID_KEY: DOCUMENT_REPORT_ID_KEY,
    WORKBOOK_LUID_KEY: DOCUMENT_REPORT_LUID_KEY,
    WORKBOOK_NAME_KEY: DOCUMENT_REPORT_NAME_KEY,
    WORKBOOK_PROJECT_NAME_KEY: DOCUMENT_REPORT_PROJECT_NAME_KEY,
    WORKBOOK_DESCRIPTION_KEY: DOCUMENT_REPORT_DESCRIPTION_KEY,
    WORKBOOK_URL_ID_KEY: DOCUMENT_REPORT_URL_ID_KEY,
}

# Maps Tableau's naming to Alexandria' naming
REPORTS_OWNER_MAP = {
    WORKBOOK_OWNER_NAME_KEY: DOCUMENT_REPORT_OWNER_NAME_KEY,
    WORKBOOK_OWNER_USERNAME_KEY: DOCUMENT_REPORT_OWNER_USERNAME_KEY,
    WORKBOOK_OWNER_EMAIL_KEY: DOCUMENT_REPORT_OWNER_EMAIL_KEY,
}


LOG = logging.getLogger(__name__)


def run(pm, opts, *args):
    es_connections.configure(default=elasticsearch_defaults(pm))

    configure_orm(connection_string=mysql_connection_string(pm))

    projects = build_tableau_projects_settings(TABLEAU_PROJECTS_MAP, pm)

    databases_map = get_databases_map()

    for certification, projects_names in projects.items():
        LOG.info("Synchronizing '%s' projects", certification)
        for project_name in projects_names:
            LOG.info("Synchronizing '%s' ('%s')", project_name, certification)
            synchronize_project(project_name, certification, pm, databases_map)


def synchronize_project(project_name, certification, pm, databases_map):
    builder = GatewayBuilder(TableauGateway, SETTINGS_MAP, REQUIRED_SETTINGS, pm)
    gateway = builder.build()

    LOG.info("Fetching '%s' data-sources", project_name)
    data_sources = gateway.get_project_data_sources(project_name)
    LOG.info("Fetch successful. Synchronizing project data-sources...")

    for data_source in data_sources:
        synchronize_data_source(data_source, certification, databases_map)


def synchronize_data_source(data_source, certification, databases_map):
    save_tableau_data_source(
        *extract_data_source_data(data_source, certification, databases_map)
    )


def extract_data_source_data(data_source, certification, databases_map):
    data_source_parser = TableauDataSourceParser(data_source)

    LOG.info("Parsing data-source representation")

    identifier = data_source_parser.identifier
    name = data_source_parser.name

    LOG.info("Synchronizing '%s' ('%s') data-source", identifier, name)

    custom_sql = data_source_parser.get_custom_sql()

    metadata_fields = map_metadata_fields_to_alexandria_naming(
        data_source_parser.get_metadata_fields()
    )

    query_fields = map_query_fields_to_alexandria_naming(
        data_source_parser.get_query_fields()
    )

    input_sources = map_tables_to_input_sources(
        data_source_parser.get_tables(), databases_map
    )

    # Tableau's workbooks are named "reports" in Alexandria
    workbooks, workbooks_total_count = data_source_parser.get_workbooks()
    reports = map_workbooks_to_reports(workbooks)

    data_source_fields = {
        DOCUMENT_NAME_KEY: name,
        CERTIFICATION_FIELD_NAME: certification,
        DOCUMENT_LUID_KEY: data_source_parser.luid,
        DOCUMENT_CUSTOM_SQL_KEY: custom_sql,
        DOCUMENT_REPORTS_TOTAL_COUNT: workbooks_total_count,
        DOCUMENT_REPORTS_KEY: create_elastic_search_objects(
            TableauDataSourceReport, reports
        ),
    }

    return (
        identifier,
        name,
        metadata_fields,
        query_fields,
        input_sources,
        data_source_fields,
    )


def save_tableau_data_source(
    identifier, name, metadata_fields, query_fields, input_sources, data_source_fields,
):
    exists, document = document_exists(
        TableauDataSourceDocumentation.Index.name, identifier
    )

    if exists:
        LOG.info("Updating data-source with ID '%s' ('%s')", identifier, name)
        update_tableau_data_source(
            document, metadata_fields, query_fields, input_sources, data_source_fields
        )
    else:
        LOG.info(
            "Saving data-source with ID '%s' ('%s') for the first time",
            identifier,
            name,
        )
        create_tableau_data_source(
            identifier, metadata_fields, query_fields, input_sources, data_source_fields
        )


def create_tableau_data_source(
    identifier, metadata_fields, query_fields, input_sources, data_source_fields
):
    document = TableauDataSourceDocumentation(
        **{
            DOCUMENT_METADATA_FIELD_ID_KEY: identifier,
            DOCUMENT_METADATA_FIELDS_KEY: create_elastic_search_objects(
                TableauDataSourceMetadataField, metadata_fields
            ),
            DOCUMENT_QUERY_FIELDS_KEY: create_elastic_search_objects(
                TableauDataSourceQueryField, query_fields
            ),
            DOCUMENT_INPUT_SOURCES_KEY: create_elastic_search_objects(
                TableauDataSourceInputSource, input_sources
            ),
            **data_source_fields,
        }
    )
    document.save()


def update_tableau_data_source(
    document,
    metadata_fields_updates,
    query_fields_updates,
    input_sources_updates,
    data_source_fields,
):
    updated_metadata_fields = synchronize_nested_list(
        document,
        DOCUMENT_METADATA_FIELDS_KEY,
        DOCUMENT_METADATA_FIELD_NAME_KEY,
        TableauDataSourceMetadataField,
        metadata_fields_updates,
        LOG,
    )

    updated_query_fields = synchronize_nested_list(
        document,
        DOCUMENT_QUERY_FIELDS_KEY,
        DOCUMENT_QUERY_FIELD_NAME_KEY,
        TableauDataSourceQueryField,
        query_fields_updates,
        LOG,
    )

    updated_input_sources = synchronize_nested_list(
        document,
        DOCUMENT_INPUT_SOURCES_KEY,
        DOCUMENT_INPUT_SOURCE_NAME_KEY,
        TableauDataSourceInputSource,
        input_sources_updates,
        LOG,
    )

    LOG.info("Saving updates")

    updates = {
        DOCUMENT_METADATA_FIELDS_KEY: updated_metadata_fields,
        DOCUMENT_QUERY_FIELDS_KEY: updated_query_fields,
        DOCUMENT_INPUT_SOURCES_KEY: updated_input_sources,
        **data_source_fields,
    }

    BaseDocType.update_document(document, updates)


def map_metadata_fields_to_alexandria_naming(metadata_fields):
    return [
        {
            alexandria_prop_name: metadata_field.get(tableau_prop_name)
            for tableau_prop_name, alexandria_prop_name in METADATA_FIELDS_MAP.items()
        }
        for metadata_field in metadata_fields
    ]


def map_query_fields_to_alexandria_naming(query_fields):
    return [
        {
            alexandria_prop_name: query_field.get(tableau_prop_name)
            for tableau_prop_name, alexandria_prop_name in QUERY_FIELDS_MAP.items()
        }
        for query_field in query_fields
    ]


def map_tables_to_input_sources(tables, databases_map):
    separator = INPUT_SOURCE_DATA_SOURCE_NAME_SEPARATOR
    input_sources = []

    for table in tables:
        database = table.database

        if not database:
            database = INPUT_SOURCE_DATABASE_DEFAULT
            LOG.info(
                "Table '%s' has not database. Defaulting to '%s'...",
                table.name,
                database,
            )

        doc_type = databases_map.get(database)
        data_source_type = INPUT_SOURCE_DATA_SOURCE_TYPE_MAP.get(database)

        if doc_type and data_source_type:
            data_source_name = f"{table.schema}{separator}{table.name}"

            doc_id = data_source_name

            if doc_type == BloodmoonTableDocumentation:
                doc_id = BloodmoonTableDocumentation.generate_id(
                    table.schema, table.name
                )
            elif doc_type == MySqlTableDocumentation:
                doc_id = MySqlTableDocumentation.build_identifier(database, table.name)

            input_sources.append(
                {
                    DOCUMENT_INPUT_SOURCE_TYPE_KEY: data_source_type,
                    DOCUMENT_INPUT_SOURCE_NAME_KEY: data_source_name,
                    DOCUMENT_INPUT_SOURCE_DATABASE_KEY: database,
                    DOCUMENT_INPUT_SOURCE_DOC_TYPE_KEY: doc_type.Index.name,
                    DOCUMENT_INPUT_SOURCE_DOC_ID_KEY: doc_id,
                }
            )
        else:
            LOG.info("Ignoring table '%s' of database '%s'", table.name, database)

    return input_sources


def map_workbooks_to_reports(workbooks):
    reports = []

    for workbook in workbooks:
        report_data = {
            alexandria_prop_name: workbook.get(tableau_prop_name)
            for tableau_prop_name, alexandria_prop_name in REPORTS_MAP.items()
        }

        owner = workbook.get(WORKBOOK_OWNER_KEY, {})

        owner_data = {
            alexandria_prop_name: owner.get(tableau_prop_name)
            for tableau_prop_name, alexandria_prop_name in REPORTS_OWNER_MAP.items()
        }

        workbook_sheets_data = workbook.get(WORKBOOK_SHEETS_KEY, {})
        sheets_count = workbook_sheets_data.get(TOTAL_COUNT_KEY)

        workbook_views_data = workbook.get(WORKBOOK_VIEWS_KEY, {})
        views_count = workbook_views_data.get(TOTAL_COUNT_KEY)

        total_counts = {
            DOCUMENT_REPORT_SHEETS_COUNT_KEY: sheets_count,
            DOCUMENT_REPORT_VIEWS_COUNT_KEY: views_count,
        }

        report = dict(**report_data, **owner_data, **total_counts)

        reports.append(report)

    return reports
