@echo off
rem Double-click to start the whole FormTrap system and open it in the browser. Same as: npm run dev:open
cd /d "%~dp0"
node tools\dev.mjs --open %*
pause
