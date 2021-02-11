import React, { useState, useEffect } from 'react';
import Modal from '@indeed/frontend-components-react/components/Modal';
import Toast from '@indeed/frontend-components-react/components/Toast';

import ModalFormHeader from './ModalFormHeader';
import ModalFormFooter from './ModalFormFooter';
import ModalFormBody from './ModalFormBody';

import styles from './ModalForm.scss';

const ToastMessage = ({ title = 'Success', message, show, onEnd, delay, type }) => {
  return (
    <Toast
      isOpen={show}
      dismissable
      type={type === 'error' ? 'danger' : 'success'}
      delay={delay}
      onExit={() => onEnd()}
    >
      <div className={styles.success_message}>
        <div>{title}</div>
        <div>{message}</div>
      </div>
    </Toast>
  );
};

const ModalForm = ({
  fieldName,
  show,
  startEditing,
  onExit,
  onSave,
  successMessage,
  messageDelay = 5000,
  initialValues,
  items,
  autocompleteItems,
  onGetIndexAutocomplete,
  onClearIndexAutocomplete,
  onRowChange,
}) => {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [row, setRow] = useState({});
  const [saved, setSaved] = useState(false);
  const [requiredName, setRequiredName] = useState('');

  const findItemOptionExtra = (item, v) =>
    item.options?.find(opt => opt.value === v || opt.extra?.onValue?.(v))?.extra;

  const setItemDependants = (item, xrow, extra) => {
    if (item.dependantFields && extra) {
      item.dependantFields.forEach(f => {
        xrow[f].extra = extra;
      });
    }
  };

  useEffect(() => {
    if (!show) return;
    const newRow = items.reduce((obj, item) => {
      const value = {
        value: initialValues[item.name],
        originalValue: initialValues[item.name],
        defaultValue: item.defaultValue,
        edited: false,
        type: item.type,
        extra: item.extra,
        alwaysSend: item.alwaysSend,
      };
      return { ...obj, [item.name]: value };
    }, {});
    items.forEach(item => {
      const xvalue = newRow[item.name]?.value;
      if (xvalue && item.options) {
        const extra = findItemOptionExtra(item, xvalue);
        setItemDependants(item, newRow, extra);
      }
      item.onEdit?.(newRow);
    });
    setEditing(startEditing);
    setRow(newRow);
    setSaved(false);
    onRowChange?.(newRow);
  }, [show]);

  const findItemByField = field => items.find(itm => itm.name === field);

  const onChangeHandler = field => ({ target: { value, checked, docId, ...rest } }) => {
    const newRow = {
      ...row,
      [field]: {
        ...row[field],
        value: docId || value || checked,
        edited: (docId || value || checked) !== row[field].originalValue,
      },
    };

    const item = findItemByField(field);
    item.onChange?.(newRow, { ...rest, value });
    const extra = findItemOptionExtra(item, value);

    setItemDependants(item, newRow, extra);

    setRow(newRow);
    onRowChange?.(newRow);
  };

  const checkRequired = () => {
    return items.every(item => {
      if (item.required && row[item.name].value === undefined) {
        setRequiredName(item.label);
        setShowError(true);
        return false;
      }
      return true;
    });
  };

  const canSave = () => Object.keys(row).some(key => row[key].edited);

  const cleanEdited = () => {
    const newRow = Object.keys(row).reduce(
      (acc, k) => ({ ...acc, [k]: { ...row[k], edited: false, originalValue: row[k].value } }),
      {}
    );
    items.forEach(item => item.onEdit?.(newRow));
    setRow(newRow);
  };

  const onSaveSuccess = () => {
    setEditing(false);
    setSaving(false);
    setShowToast(true);
    cleanEdited();
    setSaved(true);
  };
  const onSaveFailure = errMessage => {
    setShowError(true);
    setSaving(false);
    setErrorMessage(!errMessage ? 'Error saving field values' : errMessage);
  };

  const onSaveHandler = () => {
    const data = Object.keys(row).reduce((acc, key) => {
      return (row[key].alwaysSend || row[key].edited || row[key].defaultValue !== undefined) &&
        row[key].type !== 'readonly'
        ? {
            ...acc,
            [key]:
              row[key].value ||
              (row[key].defaultValue !== undefined ? row[key].defaultValue : row[key].value),
          }
        : acc;
    }, {});
    setSaving(true);
    if (checkRequired()) return onSave(data, onSaveSuccess, onSaveFailure);
  };

  const onCancelHandler = () => {
    const newRow = Object.keys(row).reduce(
      (acc, k) => ({ ...acc, [k]: { ...row[k], edited: false, value: row[k].originalValue } }),
      {}
    );
    setRow(newRow);
    setEditing(false);
  };

  return (
    <Modal isOpen={show} onExit={() => onExit(saved)} id="edit_modal_form" title="Edit Modal Form">
      <div className={styles.form_container}>
        <ToastMessage
          show={showToast}
          onEnd={() => setShowToast(false)}
          message={successMessage}
          delay={messageDelay}
        />
        <ToastMessage
          title="Error"
          type="error"
          show={showError}
          onEnd={() => {
            setShowError(false);
            setErrorMessage('');
          }}
          message={errorMessage || `Required field "${requiredName}" is empty`}
          delay={3000}
        />
        <ModalFormHeader title={fieldName} onClose={onExit} editing={editing} />
        <ModalFormBody
          items={items.filter(f => f.type !== 'invisible')}
          onChange={onChangeHandler}
          row={row}
          editing={editing}
          autocompleteItems={autocompleteItems}
          onGetIndexAutocomplete={onGetIndexAutocomplete}
          onClearIndexAutocomplete={onClearIndexAutocomplete}
        />
        <ModalFormFooter
          editing={editing}
          saving={saving}
          onEdit={() => setEditing(true)}
          onCancel={onCancelHandler}
          onSave={onSaveHandler}
          onClose={() => onExit(saved)}
          canSave={canSave()}
        />
      </div>
    </Modal>
  );
};

export default ModalForm;
