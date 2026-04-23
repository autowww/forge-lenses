/**
 * Exposes a small, read-only API for the Lenses Studio window (frameless chrome).
 */
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("lensesElectron", {
  minimize: () => ipcRenderer.invoke("win-minimize"),
  maximize: () => ipcRenderer.invoke("win-maximize"),
  close: () => ipcRenderer.invoke("win-close"),
  isMaximized: () => ipcRenderer.invoke("win-is-maximized"),
  platform: process.platform,
  onMaximizedChange: (callback) => {
    if (typeof callback !== "function") return () => {};
    const handler = (_event, maximized) => {
      callback(!!maximized);
    };
    ipcRenderer.on("win-maximized-changed", handler);
    return () => {
      ipcRenderer.removeListener("win-maximized-changed", handler);
    };
  },
});
