import { expect, test } from "@playwright/test";

test("administrator can explore and configure the workspace; viewer is read-only", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Criar acesso" }),
  ).toBeVisible();
  await page.getByLabel("Usuário", { exact: true }).fill("browser-admin");
  await page
    .getByLabel("Senha", { exact: true })
    .fill("browser-test-password-123");
  await page.getByRole("button", { name: "Criar acesso" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Encontre informações para sua pesquisa.",
    }),
  ).toBeVisible();
  const freshness = page.getByText(
    "De onde vêm estes dados e quando foram atualizados?",
    { exact: true },
  );
  await freshness.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByText("Situação das coletas registradas.", { exact: false }),
  ).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.locator(".management-menu")).not.toHaveAttribute(
    "open",
    "",
  );
  await page
    .getByRole("button", { name: "Próximo passo →", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Abra e entenda o resultado",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Próximo passo →", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Entendi, começar", exact: true })
    .click();
  await page.reload();
  await expect(
    page.getByRole("button", {
      name: "Rever os primeiros passos",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Rever os primeiros passos", exact: true })
    .click();
  await page.screenshot({
    path: "artifacts/portal-home-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "artifacts/portal-home-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("link", { name: "Ver orientações de pesquisa →" })
    .click();
  await expect(
    page.getByRole("heading", { level: 1, name: "Ajuda", exact: true }),
  ).toBeVisible();
  await page
    .getByText("Quero refinar ou salvar uma pesquisa", { exact: true })
    .click();
  await expect(
    page.getByText("Salvar pesquisa guarda os critérios na sua conta.", {
      exact: false,
    }),
  ).toBeVisible();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.getByRole("button", { name: "Instituições", exact: true }).click();
  await expect(
    page.getByText("Universidade de Teste E2E", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "+ Acompanhar", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "✓ Acompanhando" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Explorar →" }).click();
  await expect(
    page.getByRole("heading", { name: "Rede de colaboração" }),
  ).toBeVisible();
  await expect(page.locator("canvas").first()).toBeVisible();
  await page.screenshot({
    path: "artifacts/institution-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Publicações", exact: true }).click();
  await expect(
    page.getByLabel("Autor ou ORCID", { exact: true }),
  ).not.toBeVisible();
  await page.getByRole("button", { name: "Mais opções de pesquisa +" }).click();
  await expect(
    page.getByLabel("Autor ou ORCID", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name: "Computer networks integration test",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "Autores e identificadores públicos" }),
  ).toBeVisible();
  await expect(
    page
      .locator(".publication-detail")
      .getByText("Revista de Redes E2E", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Ana Silva E2E →", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Ana Silva E2E", exact: true }),
  ).toBeVisible();
  await expect(page).toHaveURL(/researchers\?id=/);
  await page
    .getByRole("link", {
      name: "Computer networks integration test →",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Computer networks integration test",
      level: 2,
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Fechar publicação", exact: true })
    .click();
  await page.getByRole("button", { name: "Início", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Pesquisar em todo o catálogo" })
    .fill("UE2E");
  await expect(
    page
      .getByRole("listbox")
      .getByRole("option", { name: /Universidade de Teste E2E/ }),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "Pesquisar em todo o catálogo" })
    .press("ArrowDown");
  await page
    .getByRole("combobox", { name: "Pesquisar em todo o catálogo" })
    .press("Enter");
  await expect(
    page.getByRole("heading", {
      name: "Universidade de Teste E2E",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("link", { name: "2025 · 1", exact: true }).click();
  await expect(page).toHaveURL(/year=2025/);
  await expect(
    page.getByRole("button", {
      name: "Computer networks integration test",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Limpar todos", exact: true }).click();
  await expect(page).toHaveURL(/\/publications$/);
  await page.getByRole("button", { name: "Mais opções de pesquisa +" }).click();
  await page
    .getByLabel("Idioma dos metadados", { exact: true })
    .selectOption("en");
  await page
    .getByLabel("Tipo de publicação", { exact: true })
    .selectOption("article");
  await page
    .getByLabel("Disponibilidade de resumo", { exact: true })
    .selectOption("true");
  await expect(
    page.getByRole("button", {
      name: "Computer networks integration test",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page).toHaveURL(/language=en/);
  await page.reload();
  await expect(
    page.getByLabel("Idioma dos metadados", { exact: true }),
  ).toHaveValue("en");
  await page.getByRole("button", { name: "Limpar todos", exact: true }).click();
  await expect(page).toHaveURL(/\/publications$/);
  await page.getByLabel("Ano inicial", { exact: true }).fill("2024");
  await page.getByLabel("Ano inicial", { exact: true }).press("Tab");
  await expect(page).toHaveURL(/year_from=2024/);
  await page.getByLabel("Acesso aberto", { exact: true }).selectOption("true");
  await expect(page).toHaveURL(/oa=true/);
  await page.getByLabel("Tema", { exact: true }).selectOption("T1");
  await expect(
    page.getByRole("button", {
      name: "Computer networks integration test",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name: "Favoritar: Computer networks integration test",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("button", {
      name: "Remover dos favoritos: Computer networks integration test",
      exact: true,
    }),
  ).toHaveAttribute("aria-pressed", "true");
  const exportLink = await page
    .getByRole("link", { name: "Baixar planilha (CSV) ↓" })
    .getAttribute("href");
  const exported = await page.request.get(exportLink!);
  expect(await exported.text()).toContain("Computer networks integration test");
  expect(await exported.text()).not.toContain("Educational biology E2E");
  await page
    .getByRole("button", { name: "Salvar pesquisa", exact: true })
    .click();
  await page.getByLabel("Nome da pesquisa", { exact: true }).fill("Redes E2E");
  await page
    .getByLabel("Avisar sobre novos resultados após as próximas coletas")
    .check();
  await page
    .getByRole("button", { name: "Salvar combinação de filtros" })
    .click();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Pesquisar", exact: true })
    .click();
  await page.getByRole("button", { name: "Redes E2E", exact: true }).click();
  await expect(page).toHaveURL(/publications\?.*year_from=2024/);
  await page.reload();
  await expect(page.getByLabel("Ano inicial", { exact: true })).toHaveValue(
    "2024",
  );
  await expect(page.getByLabel("Tema", { exact: true })).toHaveValue("T1");
  await page.goBack();
  await expect(page).toHaveURL(/search/);
  await page.goForward();
  await expect(
    page.getByRole("button", {
      name: "Computer networks integration test",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByLabel("Buscar título", { exact: true })
    .fill("zzzz-no-results");
  await expect(
    page.getByText("Nenhuma publicação corresponde a esta combinação"),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Remover todos os filtros", exact: true })
    .click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "artifacts/research-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.setViewportSize({ width: 1280, height: 900 });
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Pesquisar", exact: true })
    .click();
  await page.screenshot({
    path: "artifacts/discovery-desktop.png",
    fullPage: true,
  });
  const falseSearch = await page.request.post("/api/saved-searches", {
    headers: { "X-CampusOps": "1" },
    data: {
      name: "Sem DOI e sem resumo",
      filters: { oa: false, has_doi: false, has_abstract: false },
    },
  });
  expect(falseSearch.status()).toBe(201);
  await page
    .getByRole("button", { name: "Minhas pesquisas", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Sem DOI e sem resumo", exact: true })
    .click();
  await expect(page).toHaveURL(/oa=false/);
  await expect(page).toHaveURL(/has_doi=false/);
  await expect(page).toHaveURL(/has_abstract=false/);
  await expect(
    page.getByRole("button", { name: "Educational biology E2E", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Minhas pesquisas", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Remover pesquisa Sem DOI e sem resumo",
      exact: true,
    })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(
    page.getByRole("button", { name: "Sem DOI e sem resumo", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name: "Remover pesquisa Sem DOI e sem resumo",
      exact: true,
    })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Remover pesquisa", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Sem DOI e sem resumo", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: /^Favoritos 1$/ }).click();
  await expect(
    page.getByRole("link", {
      name: "Computer networks integration test",
      exact: true,
    }),
  ).toBeVisible();
  await page.screenshot({
    path: "artifacts/my-research-desktop.png",
    fullPage: true,
  });
  await page.locator(".management-menu > summary").click();
  await page
    .getByRole("button", { name: "Saúde das fontes e links", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Saúde das fontes e links",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByLabel("Categoria do monitoramento")
    .selectOption("publication");
  await page
    .getByRole("button", { name: "Repositório de teste E2E", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Registros que utilizam este endereço 1",
    }),
  ).toBeVisible();
  await expect(
    page.locator(".monitor-detail .detail-body > p").filter({
      hasText: "Certificado de exemplo válido, com vencimento em 5 dias.",
    }),
  ).toBeVisible();
  await page
    .getByText("Certificados validados no trajeto", { exact: true })
    .click();
  await expect(
    page.getByText("Emissor: CA de teste", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "artifacts/monitoring-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "artifacts/monitoring-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page
    .getByRole("button", { name: "Fechar diagnóstico", exact: true })
    .click();
  await page.getByLabel("Categoria do monitoramento").selectOption("api");
  await page
    .getByRole("button", { name: "Verificar APIs agora", exact: true })
    .click();
  await expect(
    page.locator(".monitor-table .badge").filter({ hasText: /^Na fila$/ }),
  ).toHaveCount(5);
  await page.getByRole("button", { name: "Automações", exact: true }).click();
  await page.getByLabel("Nome da regra").fill("Browser networks radar");
  await page.getByRole("button", { name: "Testar regra sem executar" }).click();
  await expect(page.getByText(/registros compatíveis/)).toBeVisible();
  await page.getByRole("button", { name: "Criar regra", exact: true }).click();
  await expect(
    page.getByRole("cell", {
      name: "Browser networks radar Ativa",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Criar agendamento", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Pausar", exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Fluxos", exact: true }).click();
  await page.getByLabel("Nome do fluxo", { exact: true }).fill("Rotina E2E");
  await page.getByRole("button", { name: "Criar fluxo", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Rotina E2E Ativo" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Agendar fluxo", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Prévia dos próximos horários" })
    .click();
  await expect(page.locator(".schedule-preview li")).toHaveCount(5);
  await page
    .getByRole("button", { name: "Salvar agenda", exact: true })
    .click();
  await expect(
    page.getByRole("cell", { name: "Rotina E2E · agenda", exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Iniciar fluxo", exact: true })
    .click();
  await page.getByRole("button", { name: "Pausar fluxo", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Retomar fluxo", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: /Ver progresso da etapa/ }).click();
  await expect(
    page.getByRole("button", { name: "Retomar pelo checkpoint", exact: true }),
  ).toBeVisible();
  await page.locator(".explore-menu > summary").click();
  await page.getByRole("button", { name: "Relatórios", exact: true }).click();
  await page
    .getByLabel("Nome do relatório", { exact: true })
    .fill("Redes privadas E2E");
  await page
    .getByLabel("Critérios do relatório")
    .selectOption({ label: "Redes E2E" });
  await page.getByRole("button", { name: "Criar modelo de relatório" }).click();
  await page.getByRole("button", { name: "Gerar relatório agora" }).click();
  await expect(
    page.getByRole("cell", { name: "Na fila", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "artifacts/automation-reports.png",
    fullPage: true,
  });
  if (
    !(await page
      .getByRole("button", { name: "Integrações", exact: true })
      .isVisible())
  )
    await page.locator(".management-menu > summary").click();
  for (const tab of [
    "Integrações",
    "Execuções",
    "Incidentes",
    "Radar e resumo",
    "Qualidade",
    "Pesquisadores",
    "Dados abertos",
    "Revisão de registros",
    "Alterações",
    "Limites e recuperação",
  ]) {
    if (["Pesquisadores", "Dados abertos"].includes(tab))
      await page.locator(".explore-menu > summary").click();
    await page.getByRole("button", { name: tab, exact: true }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: tab, exact: true }),
    ).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
  }
  await page
    .getByRole("button", { name: "Administração", exact: true })
    .click();
  await page.getByLabel("Usuário", { exact: true }).fill("browser-viewer");
  await page.getByLabel("Senha inicial").fill("browser-viewer-password-123");
  await page
    .getByRole("button", { name: "Criar usuário", exact: true })
    .click();
  await expect(
    page.getByRole("cell", { name: "browser-viewer", exact: true }),
  ).toBeVisible();
  await page.locator(".explore-menu > summary").click();
  await page.getByRole("button", { name: "Minha conta", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Sessões ativas", exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Senha atual", { exact: true })
    .fill("browser-test-password-123");
  await page
    .getByLabel("Nova senha", { exact: true })
    .fill("browser-new-password-123");
  await page
    .getByLabel("Confirmar nova senha", { exact: true })
    .fill("browser-new-password-123");
  await page
    .getByRole("button", { name: "Alterar senha", exact: true })
    .click();
  await expect(
    page.getByText("Senha alterada. As outras sessões foram encerradas.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "artifacts/account-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.getByRole("button", { name: "Sair da conta" }).click();
  await expect(
    page.getByRole("heading", { name: "Bem-vindo de volta." }),
  ).toBeVisible();
  await page.getByLabel("Usuário", { exact: true }).fill("browser-viewer");
  await page
    .getByLabel("Senha", { exact: true })
    .fill("browser-viewer-password-123");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "Encontre informações para sua pesquisa.",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Administração", exact: true }),
  ).toHaveCount(0);
  if (
    !(await page
      .getByRole("button", { name: "Integrações", exact: true })
      .isVisible())
  )
    await page.locator(".management-menu > summary").click();
  await page.getByRole("button", { name: "Integrações", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Configurar coleta" }),
  ).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "artifacts/integrations-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Pesquisar", exact: true })
    .click();
  await page
    .getByRole("button", { name: "★ Meus favoritos", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: /^0 resultados/ }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
