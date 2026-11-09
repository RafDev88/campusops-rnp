# Como contribuir

## Organização das mudanças

Use branches curtas a partir da `main`: `feat/filtros-publicacoes`, `fix/retomada-coleta` ou `docs/guia-backend`. Faça um commit por mudança coerente e inclua seus testes quando aplicável. Evite misturar ajustes visuais, alteração de banco e correções de integração sem relação entre si.

Examine `git status` e `git diff --staged` antes de confirmar. Não adicione `.env`, dados locais, backups, tokens, certificados privados ou documentos pessoais. O certificado público de autoridade em `backend/certificates` é parte necessária da cadeia TLS e pode ser versionado.

## Mensagens: Conventional Commits

Conventional Commits é uma convenção deste projeto, não uma exigência do próprio Git:

```text
tipo(escopo): descrição objetiva no imperativo
```

Tipos aceitos: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore` e `revert`. O escopo é opcional; use nomes estáveis como `api`, `search`, `auth`, `monitoring`, `web`, `storage`, `docker` ou `deps`. O assunto deve ter até 100 caracteres, em uma linha, sem ponto final. Use português ou inglês de maneira consistente na mudança.

```text
feat(search): adiciona filtro por idioma
fix(auth): invalida outras sessões após trocar senha
test(monitoring): cobre redirecionamento para rede privada
docs(api): explica o cabeçalho de proteção CSRF
```

Use o corpo para explicar motivo, efeitos e validação quando isso ajudar a revisão. Mudanças incompatíveis devem usar `!` após tipo/escopo e um rodapé `BREAKING CHANGE: ...` explicando impacto e migração. Não declare uma mudança incompatível apenas por alterar arquivos internos.

Para habilitar a validação local da mensagem, execute na raiz:

```powershell
git config --local core.hooksPath .githooks
```

O hook usa Python 3 e não consulta serviços externos. Essa configuração é local e precisa ser aplicada em cada clone. O GitHub Actions verifica os commits enviados, mesmo quando o hook não foi habilitado.

## Validação e pull requests

Execute os testes adequados ao comportamento alterado. Para backend: `python -m pytest tests -q` no diretório `backend`; para frontend: `npm run build` em `frontend`. Alterações de rotas, modelos ou filtros também exigem regenerar `scripts/document-backend.py` e conferir `--check`. Os detalhes estão em `backend/README.md`.

Abra um pull request com problema, resultado, evidências e limites. Informe migração de banco, alterações de acesso e riscos operacionais. Descreva testes efetivamente executados, distinguindo os planejados. Uma alteração pequena não precisa de testes que apenas repitam a implementação.

Revise antes de integrar. Prefira **squash merge** quando um PR representa uma única mudança, com título compatível com Conventional Commits; preserve commits separados quando eles forem coerentes e úteis à revisão. Não rebase nem force-push em histórico compartilhado sem combinar com quem o utiliza. Se uma reorganização autorizada for necessária, preserve uma referência anterior e use `--force-with-lease` com o SHA esperado.

## Importação inicial reorganizada

O código da versão 0.8 foi inicialmente publicado em um único commit. Seu conteúdo foi posteriormente distribuído por responsabilidades para facilitar inspeção, mantendo os mesmos arquivos da aplicação. Essa sequência é uma organização da importação inicial, não uma reconstrução das datas ou da autoria de cada etapa do desenvolvimento. Alguns commits intermediários ainda dependem de módulos adicionados adiante; a validação integral se aplica ao estado final.

A tag `backup/pre-history-reorganization-20261109` preserva a publicação original. Para clones feitos antes da reorganização, faça backup das alterações locais e use um novo clone se não estiver familiarizado com a reconciliação de históricos. Não descarte trabalho local para atualizar.
