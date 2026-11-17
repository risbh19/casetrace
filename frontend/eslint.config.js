import tseslint from 'typescript-eslint'

export default [
  { ignores: ['dist'] },
  ...tseslint.configs.recommended,
  { files: ['src/**/*.{ts,tsx}'], rules: { 'no-debugger': 'error' } },
]
