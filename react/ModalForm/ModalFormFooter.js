import React from 'react';
import { Button } from '@indeed/ifl-components';

import { ReportAProblem } from 'components/Common/CompleteDocumentationLayout';

import styles from './ModalForm.scss';

const ModalFormFooter = ({ editing, saving, canSave, onEdit, onCancel, onSave, onClose }) => (
  <div className={styles.form_footer}>
    <span>
      <ReportAProblem className={styles.report_problem} />
    </span>
    {canSave && <span role="textbox">Select &quot;Save&quot; to apply edits</span>}
    <Button
      className={styles.first_footer_button}
      variant="tertiary"
      size="md"
      onClick={editing ? onCancel : onEdit}
    >
      {editing ? 'Cancel' : 'Edit'}
    </Button>
    <Button
      size="md"
      variant="secondary"
      onClick={editing ? onSave : onClose}
      disabled={editing && (!canSave || saving)}
    >
      {editing ? 'Save' : 'Close'}
    </Button>
  </div>
);

export default ModalFormFooter;
