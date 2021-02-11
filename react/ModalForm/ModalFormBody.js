import React from 'react';

import ModalFormItem from './ModalFormItem';

import styles from './ModalForm.scss';

const ModalFormBody = ({
  items,
  onChange,
  row,
  editing,
  autocompleteItems,
  onGetIndexAutocomplete,
  onClearIndexAutocomplete,
}) => (
  <div className={styles.form_body}>
    {items
      .filter(f => !f.hideInForm)
      .map(item => {
        const record = row[item.name] || {};
        return (
          <ModalFormItem
            key={item.name}
            type={item.type}
            value={record.value}
            edited={record.edited}
            extra={record.extra}
            onChange={onChange(item.name)}
            field={item.name}
            textRows={item.textRows}
            size={item.size}
            options={item.options}
            label={item.label}
            placeholder={item.placeholder}
            required={item.required}
            editing={editing}
            preFormat={item.preFormat}
            infoVariable={item.infoVariable}
            onValue={() => item.onValue?.(row, editing)}
            autocompleteItems={autocompleteItems}
            onGetIndexAutocomplete={onGetIndexAutocomplete}
            onClearIndexAutocomplete={onClearIndexAutocomplete}
            specialFormat={item.specialFormat}
          />
        );
      })}
  </div>
);

export default ModalFormBody;
