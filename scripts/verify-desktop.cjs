const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { _electron: electron } = require('../frontend/node_modules/playwright');

(async () => {
  const env = { ...process.env, CAMPUSOPS_QA: '1' };
  delete env.ELECTRON_RUN_AS_NODE;
  const application = await electron.launch({
    executablePath: require('../desktop/node_modules/electron'),
    args: [path.resolve(__dirname, '../desktop')], env,
  });
  try {
    const page = await application.firstWindow();
    await page.locator('.login-card, .shell').waitFor();
    assert.equal(await page.title(), 'CampusOps | Operações universitárias');
    assert.equal(await page.evaluate(() => typeof require), 'undefined');
    const preferences = await application.evaluate(({ BrowserWindow }) => {
      const window = BrowserWindow.getAllWindows()[0];
      const { sandbox, contextIsolation, nodeIntegration } = window.webContents.getLastWebPreferences();
      return { sandbox, contextIsolation, nodeIntegration, visible: window.isVisible() };
    });
    assert.deepEqual(preferences, { sandbox: true, contextIsolation: true, nodeIntegration: false, visible: false });
    const directory = path.resolve(__dirname, '../desktop/artifacts');
    await fs.mkdir(directory, { recursive: true });
    await page.screenshot({ path: path.join(directory, 'desktop-login.png') });
    console.log('Electron: interface loaded; sandbox and context isolation verified.');
  } finally { await application.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
