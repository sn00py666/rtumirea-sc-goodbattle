import { mkdir, writeFile } from 'fs/promises'
import openapiTS, { astToString } from 'openapi-typescript'
import { factory } from 'typescript'
import 'dotenv/config'

const OPENAPI_SPEC_URL = `${process.env.VITE_API_URL}/openapi.json`

console.log('Generating API types...')

const ast = await openapiTS(OPENAPI_SPEC_URL, {
  transform({ format, nullable }, { path }) {
    if (format !== 'binary' || !path) {
      return
    }

    const typeName = path.includes('multipart~1form-data')
      ? 'File'
      : path.includes('application~1octet-stream')
        ? 'Blob'
        : null

    if (!typeName) {
      return
    }

    const node = factory.createTypeReferenceNode(typeName)

    return nullable
      ? factory.createUnionTypeNode([
          node,
          factory.createTypeReferenceNode('null'),
        ])
      : node
  },
})

const output = astToString(ast)

await mkdir('./src/api/__generated__').catch(() => {})
await writeFile('./src/api/__generated__/schema.d.ts', output)

console.log('✓ Types generated successfully')
