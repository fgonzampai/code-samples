import React from 'react';
import CloseButton from '@indeed/frontend-components-react/components/CloseButton';

import styles from './ModalForm.scss';

const ModalFormHeader = ({ title, editing, onClose }) => (
  <div className={styles.form_header}>
    <span>{title}</span>
    {!editing && <CloseButton type="button" onClick={onClose} />}
  </div>
);

export default ModalFormHeader;
