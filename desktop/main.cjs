const { app, BrowserWindow, dialog, session, shell } = require('electron');

const origin = 'http://localhost:8080';
let mainWindow;
if (!app.requestSingleInstanceLock()) app.quit();
app.on('second-instance', () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  }
});

app.whenReady().then(async () => {
  session.defaultSession.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  session.defaultSession.setPermissionCheckHandler(() => false);
  mainWindow = new BrowserWindow({
    title: 'CampusOps', width: 1440, height: 960, minWidth: 800, minHeight: 600,
    backgroundColor: '#f5f7fa', show: false,
    webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true, webSecurity: true },
  });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    try {
      if (new URL(url).protocol === 'https:') shell.openExternal(url);
    } catch { /* Invalid URLs never leave the application. */ }
    return { action: 'deny' };
  });
  mainWindow.webContents.on('will-navigate', (event, url) => {
    try { if (new URL(url).origin !== origin) event.preventDefault(); }
    catch { event.preventDefault(); }
  });
  mainWindow.once('ready-to-show', () => { if (process.env.CAMPUSOPS_QA !== '1') mainWindow.show(); });
  try { await mainWindow.loadURL(origin); }
  catch {
    dialog.showErrorBox('CampusOps indisponível', 'Inicie os serviços com docker compose up -d e abra o aplicativo novamente.');
    app.quit();
  }
});
app.on('window-all-closed', () => app.quit());
