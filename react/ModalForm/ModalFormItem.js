import React, { useState } from 'react';
import Autocomplete from '@indeed/frontend-components-react/components/Forms/Autocomplete/component';
import ReactHtmlParser from 'react-html-parser';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faInfoCircle } from '@fortawesome/free-solid-svg-icons';

import Linkify from 'containers/Common/editable/parseLinks';
import Variable from 'containers/Common/Variables';
import TextAreaField from 'components/IndeedComponents/TextAreaField';
import CheckboxField from 'components/IndeedComponents/CheckboxField';
import SelectFormField from 'components/IndeedComponents/SelectFormField';
import InfoMenu from 'components/Common/InfoMenu';
import { parseLogEventForeignKey } from 'shared/utils';

import styles from './ModalForm.scss';

const ModalFormItem = ({
  type,
  editing,
  field,
  value,
  placeholder,
  edited,
  label,
  options,
  textRows = 4,
  preFormat = false,
  infoVariable,
  required = false,
  extra,
  autocompleteItems,
  onGetIndexAutocomplete,
  onClearIndexAutocomplete,
  onChange,
  size = 'sm',
  onValue,
  specialFormat,
}) => {
  const [info, setInfo] = useState(false);

  const getOptionValueLabel = () => {
    const opt = options.find(o => {
      return o.value === value || o.extra?.onValue?.(value);
    });
    return opt?.label || value;
  };

  const getOptionSelectValue = v => {
    const opt = options.find(o => {
      return o.value === v || o.extra?.onValue?.(v);
    });
    return opt?.value || v;
  };

  const getValue = () => {
    const xvalue = type === 'select' ? getOptionValueLabel() : onValue?.(value) || value;
    switch (typeof xvalue) {
      case 'boolean':
        return xvalue ? 'Yes' : 'No';
      case 'undefined':
        return 'none';
      default:
        return xvalue;
    }
  };

  const autoItems =
    autocompleteItems?.results?.reduce(
      (acc, res) => [...acc, ...res.results.map(r => ({ ...r, docType: res.doc_type }))],
      []
    ) || [];

  const getComponent = () => {
    switch (type) {
      case 'select':
        return (
          <SelectFormField
            name={field}
            options={options}
            value={getOptionSelectValue(value)}
            onChange={onChange}
          />
        );
      case 'checkbox':
        return (
          <CheckboxField
            checked={value === true}
            name={field}
            label={placeholder}
            value=""
            onChange={onChange}
            size={size}
          />
        );
      case 'readonly':
        return <span className={styles.item_value}>{getValue()}</span>;
      case 'autocomplete':
        return (
          <Autocomplete
            label=""
            type="text"
            name={field}
            onFocus={onClearIndexAutocomplete}
            onChange={(e, text) => {
              if (extra?.docType !== 'text' && extra?.docType?.length > 0) {
                onGetIndexAutocomplete(extra.docType, text);
              } else {
                onChange({
                  target: {
                    name: field,
                    value: text,
                  },
                });
              }
            }}
            enableDebounce
            debounceWait={500}
            placeholder="Enter a document name"
            onItemSelect={(e, displayValue, text) => {
              onChange({
                target: {
                  name: field,
                  value: text.name,
                  docType: text.docType,
                  docId: text.id,
                },
              });
            }}
            items={autoItems.map(f => {
              return {
                value: { id: f.id, name: f.name_suggest, docType: f.docType },
                displayValue: f.name_suggest,
                component: <span>{f.name_suggest}</span>,
                ariaLabel: f.id,
              };
            })}
            initialValue={onValue?.() || value}
          />
        );
      default:
        return <TextAreaField name={field} onChange={onChange} value={value} rows={textRows} />;
    }
  };

  const valueClass = typeof value === 'undefined' ? styles.None : '';

  const xvalue = onValue() || value;

  const formatValue = () => {
    switch (specialFormat) {
      case 'foreign_key':
        return value ? parseLogEventForeignKey(value) : getValue();
      default:
        return getValue();
    }
  };

  const FieldValue =
    typeof xvalue === 'object' ? (
      xvalue
    ) : specialFormat ? (
      formatValue()
    ) : (
      <Linkify properties={{ target: '_blank' }}>{ReactHtmlParser(getValue())}</Linkify>
    );

  return (
    <div className={styles.form_item}>
      <div className={styles.label}>
        {label}
        {required && <span className={styles.required}>*</span>}
        {infoVariable ? (
          <>
            <FontAwesomeIcon icon={faInfoCircle} onClick={() => setInfo(true)} />
            {info && (
              <InfoMenu className={styles.field_info} onClickOutside={() => setInfo(!info)}>
                <Variable name={infoVariable} title={`**${label}**\n\n`} />
              </InfoMenu>
            )}
          </>
        ) : null}
        {editing && <span className={styles.edited}>{edited ? 'EDITED' : ''}</span>}
      </div>
      {editing && type !== 'checkbox' && <div className={styles.placeholder}>{placeholder}</div>}
      {editing ? (
        getComponent()
      ) : (
        <span className={`${styles.item_value} ${valueClass}`}>
          {preFormat ? <pre>{FieldValue}</pre> : FieldValue}
        </span>
      )}
    </div>
  );
};

export default ModalFormItem;
