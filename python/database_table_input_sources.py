from flask_restx import Namespace, Model
from flask_restx.fields import String, List, Nested
from datasearchtool.models import provide_session
from datasearchtool.doctype.base import BaseDocType
from datasearchtool.doctype.common import INNER_DOC_ID
from datasearchtool.doctype.databasetable import DatabaseTableInputSourceField
from datasearchtool.utils.elastic_search import (
    create_elastic_search_objects,
    get_doc_type,
    remove_from_nested_list,
)
from datasearchtool.common.relationships import (
    handle_relationships,
    INPUT_SOURCE_FIELDS,
)
from datasearchtool.common.datasets import get_database_table_doc_types
from datasearchtool.webapp.api.utils import parse_url_multiple_parameter
from datasearchtool.webapp.api.namespaces.utils import (
    add_models_to_namespace,
    get_document_or_raise,
    validate_identifiers_exist_in_nested_list,
)
from datasearchtool.webapp.api.namespaces.spec import (
    build_doc_type_spec,
    takes_input_model,
)
from datasearchtool.utils.elastic_search import get_elastic_search_objects_dicts
from datasearchtool.webapp.api.namespaces.input_sources import (
    InputSourceResource,
    DOC_NAME,
    DATA_SOURCE_TYPE_ENUM,
    DATA_SOURCE_TYPE_FIELD_NAME,
    DATA_SOURCE_NAME_FIELD_NAME,
)


BaseInputSourceModel = build_doc_type_spec(DatabaseTableInputSourceField)

InputSourceModel = Model.clone(
    "DatabaseTableInputSourceModel",
    BaseInputSourceModel,
    {
        DATA_SOURCE_TYPE_FIELD_NAME: String(enum=DATA_SOURCE_TYPE_ENUM, required=True),
        DATA_SOURCE_NAME_FIELD_NAME: String(required=True),
    },
)

CompleteInputSourceModel = Model.clone(
    "DatabaseTableCompleteInputSourceModel", InputSourceModel, {DOC_NAME: String(),},
)

InputSourceEditionModel = Model(
    "DatabaseTableInputSourceEditionModel",
    {INPUT_SOURCE_FIELDS: List(Nested(InputSourceModel))},
)

CompleteInputSourcesListModel = Model(
    "DatabaseTableCompleteInputSourcesListModel",
    {INPUT_SOURCE_FIELDS: List(Nested(CompleteInputSourceModel))},
)


MODELS = [
    BaseInputSourceModel,
    InputSourceModel,
    CompleteInputSourceModel,
    InputSourceEditionModel,
    CompleteInputSourcesListModel,
]


namespace = Namespace("Database Table Input Sources")


add_models_to_namespace(MODELS, namespace)


DOC_TYPE_PARAMETER = "doc_type"
DOC_ID_PARAMETER = "doc_id"


ROUTE_TEMPLATE_DOC_TYPE_PARAMETER = "allowed_doc_types_parameter"
ROUTE_TEMPLATE = f"/{{{ROUTE_TEMPLATE_DOC_TYPE_PARAMETER}}}/<{DOC_ID_PARAMETER}>"
INPUT_SOURCE_IDENTIFIER_PARAMETER = "input_source_identifier"


DATABASE_TABLE_INDEXES = [
    doc_type.Index.name for doc_type in get_database_table_doc_types()
]


def build_route(indexes):
    any_of_indexes = ",".join(indexes)

    doc_type_parameter = f"<any({any_of_indexes}):{DOC_TYPE_PARAMETER}>"

    route = ROUTE_TEMPLATE.format(
        **{ROUTE_TEMPLATE_DOC_TYPE_PARAMETER: doc_type_parameter}
    )

    return route


@namespace.route(
    f"{build_route(DATABASE_TABLE_INDEXES)}/<{INPUT_SOURCE_IDENTIFIER_PARAMETER}>"
)
@namespace.response(404, "The document does not exist")
class DatabaseTableInputSourceResource(InputSourceResource):
    @staticmethod
    def extract_parameters(parameters):
        index = parameters.pop(DOC_TYPE_PARAMETER)
        doc_id = parameters.pop(DOC_ID_PARAMETER)
        input_source_id = parameters.pop(INPUT_SOURCE_IDENTIFIER_PARAMETER)
        return index, doc_id, input_source_id

    @namespace.response(
        200, "Read a specific input source", CompleteInputSourceModel,
    )
    def get(self, **kwargs):
        (
            index,
            doc_id,
            input_source_id,
        ) = DatabaseTableInputSourceResource.extract_parameters(kwargs)

        doc_type = get_doc_type(index)
        document = get_document_or_raise(doc_type, doc_id)

        return self._do_get_input_source(document, INPUT_SOURCE_FIELDS, input_source_id)

    @namespace.expect(InputSourceModel, validate=True)
    @takes_input_model(InputSourceModel, skip_none=True)
    @namespace.response(
        200, "The document has been successfully updated", CompleteInputSourceModel,
    )
    @provide_session
    def put(self, session, **kwargs):
        (
            index,
            doc_id,
            input_source_id,
        ) = DatabaseTableInputSourceResource.extract_parameters(kwargs)

        doc_type = get_doc_type(index)
        document = get_document_or_raise(doc_type, doc_id)

        return self._do_put(
            doc_type, document.meta.id, document, input_source_id, kwargs, session,
        )

    def _do_put(
        self, doc_type, document_id, document, input_source_id, fields, session
    ):
        updated_input_sources = InputSourceResource.update_input_source_on_list(
            document, input_source_id, fields, INPUT_SOURCE_FIELDS
        )

        updated_document = update_input_source_fields(
            doc_type, document_id, document, updated_input_sources, session
        )

        input_source = InputSourceResource.get_input_source_or_raise(
            updated_document, input_source_id, INPUT_SOURCE_FIELDS
        )

        serialized = input_source.to_dict()

        InputSourceResource.add_additional_properties_to_input_source(serialized)

        return serialized, 200

    @namespace.doc(description="Delete an input source from a document")
    @namespace.response(204, "Input source successfully deleted")
    @provide_session
    def delete(self, session, **kwargs):
        (
            index,
            doc_id,
            input_source_id,
        ) = DatabaseTableInputSourceResource.extract_parameters(kwargs)

        doc_type = get_doc_type(index)
        document = get_document_or_raise(doc_type, doc_id)

        return self._do_delete(doc_type, doc_id, document, input_source_id, session)

    def _do_delete(self, doc_type, doc_id, document, input_source_id, session):
        input_source_identifiers = parse_url_multiple_parameter(input_source_id)

        input_sources = getattr(document, INPUT_SOURCE_FIELDS)

        validate_identifiers_exist_in_nested_list(
            input_sources, INPUT_SOURCE_FIELDS, INNER_DOC_ID, input_source_identifiers
        )
        updates = {
            INPUT_SOURCE_FIELDS: remove_from_nested_list(
                input_sources, INNER_DOC_ID, input_source_identifiers
            ),
        }

        handle_relationships(document, doc_id, doc_type, session, updates=updates)

        BaseDocType.update_document(document, updates)

        return "", 204


@namespace.route(build_route(DATABASE_TABLE_INDEXES))
@namespace.response(404, "No document exists with the provided identifier")
class DatabaseTableInputSourcesResource(InputSourceResource):
    @namespace.response(
        200, "List of input sources", CompleteInputSourcesListModel,
    )
    def get(self, **kwargs):
        index = kwargs.pop(DOC_TYPE_PARAMETER)
        doc_id = kwargs.pop(DOC_ID_PARAMETER)

        doc_type = get_doc_type(index)
        document = get_document_or_raise(doc_type, doc_id)

        return self._return_input_sources_list(document, INPUT_SOURCE_FIELDS)

    @namespace.expect(InputSourceModel, validate=True)
    @takes_input_model(InputSourceModel, skip_none=True)
    @namespace.response(
        201, "The input source has been successfully created", CompleteInputSourceModel,
    )
    @provide_session
    def post(self, session, **kwargs):
        index = kwargs.pop(DOC_TYPE_PARAMETER)
        doc_id = kwargs.pop(DOC_ID_PARAMETER)

        doc_type = get_doc_type(index)
        document = get_document_or_raise(doc_type, doc_id)

        return self._do_post(doc_type, document.meta.id, document, kwargs, session)

    def _do_post(self, doc_type, document_id, document, fields, session):
        current_input_sources = getattr(document, INPUT_SOURCE_FIELDS)
        updated_input_sources = get_elastic_search_objects_dicts(current_input_sources)

        input_source = DatabaseTableInputSourceField(**fields)
        serialized_input_source = input_source.to_dict()
        updated_input_sources.append(serialized_input_source)

        update_input_source_fields(
            doc_type, document_id, document, updated_input_sources, session
        )

        InputSourceResource.add_additional_properties_to_input_source(
            serialized_input_source
        )

        return serialized_input_source, 201


def update_input_source_fields(
    doc_type, document_id, document, input_source_fields, session
):
    updated_input_source_fields = create_elastic_search_objects(
        DatabaseTableInputSourceField, input_source_fields,
    )

    updates = {INPUT_SOURCE_FIELDS: updated_input_source_fields}

    handle_relationships(document, document_id, doc_type, session, updates=updates)

    BaseDocType.update_document(document, updates)

    return document
