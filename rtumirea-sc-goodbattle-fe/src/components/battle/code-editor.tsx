import { cpp } from '@codemirror/lang-cpp'
import { java } from '@codemirror/lang-java'
import { javascript } from '@codemirror/lang-javascript'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'
import CodeMirror from '@uiw/react-codemirror'
import { useMemo } from 'react'

const LANGUAGE_EXTENSIONS: Record<string, () => ReturnType<typeof javascript>> =
  {
    cpp: () => cpp(),
    java: () => java(),
    javascript: () => javascript(),
    python: () => python(),
    typescript: () => javascript({ typescript: true }),
  }

function CodeEditor({
  code,
  language,
  onChange,
  readOnly = false,
}: {
  code: string
  language: string
  onChange?: (value: string) => void
  readOnly?: boolean
}) {
  const extensions = useMemo(() => {
    const langExt = LANGUAGE_EXTENSIONS[language]
    return langExt ? [langExt()] : []
  }, [language])

  return (
    <div className="h-full overflow-auto">
      <CodeMirror
        basicSetup={{
          bracketMatching: true,
          closeBrackets: true,
          foldGutter: false,
          lineNumbers: true,
        }}
        editable={!readOnly}
        extensions={extensions}
        onChange={onChange}
        readOnly={readOnly}
        theme={oneDark}
        value={code}
      />
    </div>
  )
}

export { CodeEditor }
