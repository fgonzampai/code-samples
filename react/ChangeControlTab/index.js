import React, { useEffect, useState } from 'react';
import { connect } from 'react-redux';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCheck } from '@fortawesome/free-solid-svg-icons';
import classnames from 'classnames';
import ReactMarkDown from 'react-markdown/with-html';
import SearchResultProgressIndicator from 'components/Common/SearchResultProgressIndicator';
import { getChangeControlUrl, getChangeControlStatus } from 'store/actions/changeControl';

import styles from './ChangeControlTab.scss';

export const FOUND_STATUS = 200;
export const STATUS_UP_TO_DATE = 'UP_TO_DATE';
export const STATUS_CHANGED = 'CHANGED';
export const STATUS_UNKNOWN = 'UNKNOWN';

const TITLE_VARIABLE = 'change_control:title';
const NOT_FOUND_VARIABLE = 'change_control:not_found';
const LOADING_MESSAGE = 'Loading, please wait ...';

export const ChangeControlStatus = ({ status, changes }) => {
  const changesText =
    status === STATUS_CHANGED ? (
      `(${changes})`
    ) : status === STATUS_UP_TO_DATE ? (
      <FontAwesomeIcon icon={faCheck} color="green" />
    ) : (
      ''
    );
  return (
    <span>
      {`Change Control `}
      <span className={styles.change_control_status_count}>{changesText}</span>
    </span>
  );
};

export const useChangeControlStatus = (docType, id) => {
  const [status, setStatus] = useState(null);
  const [statusCode, setStatusCode] = useState(null);
  const [changes, setChanges] = useState(null);

  useEffect(() => {
    async function getStatus() {
      const response = await getChangeControlStatus(docType, id);
      if (response.status === FOUND_STATUS) {
        const data = await response.json();
        setChanges(data.numberOfChanges);
        setStatus(data.status);
      }
      setStatusCode(response.status);
    }
    getStatus();
  }, [id]);

  return [status, statusCode, changes];
};

const MarkdownMessage = ({ message, className }) => (
  <div className={className}>
    <ReactMarkDown source={message} escapeHtml={false} />
  </div>
);

const DocumentStatus = ({ status, onLoad, loading, docType, indexName }) => {
  switch (status) {
    case STATUS_UP_TO_DATE:
    case STATUS_UNKNOWN:
      return <div className={styles.status_up_to_date}>The Index status is{` : "${status}"`}</div>;
    default:
      return (
        <iframe
          src={getChangeControlUrl(docType, indexName)}
          width="1000"
          height="1400"
          title="change-control"
          onLoad={() => onLoad(false)}
          className={classnames({ [styles.loading]: loading })}
        />
      );
  }
};

const ChangeControlTab = ({ title, notFoundMessage, indexName, statusCode, status, docType }) => {
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(statusCode === FOUND_STATUS && status === STATUS_CHANGED);
  }, [indexName, status, statusCode]);

  return statusCode === FOUND_STATUS ? (
    <div className={styles.change_control_container}>
      {loading ? <SearchResultProgressIndicator size="md" text={LOADING_MESSAGE} /> : null}
      <MarkdownMessage
        message={title}
        className={classnames(styles.change_control_title, { [styles.loading]: loading })}
      />
      <DocumentStatus
        loading={loading}
        onLoad={setLoading}
        status={status}
        indexName={indexName}
        docType={docType}
      />
    </div>
  ) : statusCode && statusCode !== FOUND_STATUS ? (
    <MarkdownMessage message={notFoundMessage} className={styles.change_control_not_found} />
  ) : null;
};

const mapStateToProps = (state, ownProps) => {
  return {
    title: state.variableState.variables?.[TITLE_VARIABLE],
    notFoundMessage: state.variableState.variables?.[NOT_FOUND_VARIABLE],
    ...ownProps,
  };
};

export default connect(mapStateToProps)(ChangeControlTab);
