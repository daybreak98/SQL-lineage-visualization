import type { FC } from 'react';
import Editor, { type OnMount } from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import { useWorkbenchStore } from '../stores/workbenchStore';

/**
 * SqlEditor — Monaco Editor 封装
 * SQL 语法高亮。P0 不做 completion/hover。
 */
const SqlEditor: FC = () => {
  const sql = useWorkbenchStore((s) => s.sql);
  const setSql = useWorkbenchStore((s) => s.setSql);
  const dialect = useWorkbenchStore((s) => s.dialect);
  const pageMode = useWorkbenchStore((s) => s.pageMode);

  const handleMount: OnMount = (editorInstance: editor.IStandaloneCodeEditor) => {
    // §23: MonacoAdapter Shell — reveal / markers / decorations
    // P0 阶段仅注册实例引用，后续 M6 实现 SourceLocation guard
    editorInstance.focus();
  };

  const handleChange = (value: string | undefined) => {
    setSql(value ?? '');
  };

  return (
    <div className="sql-editor" data-page-mode={pageMode}>
      <div className="sql-editor-header">
        <span className="sql-editor-label">SQL Editor</span>
        <span className="sql-editor-dialect-badge">{dialect}</span>
      </div>
      <Editor
        height="100%"
        language="sql"
        value={sql}
        onChange={handleChange}
        onMount={handleMount}
        theme="vs"
        options={{
          minimap: { enabled: false },
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          fontSize: 13,
          fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
          tabSize: 2,
          automaticLayout: true,
          // P0: 不做 completion/hover
          suggestOnTriggerCharacters: false,
          quickSuggestions: false,
          parameterHints: { enabled: false },
          hover: { enabled: false },
        }}
        loading={<div className="sql-editor-loading">Loading editor...</div>}
      />
    </div>
  );
};

export default SqlEditor;
