const vscode = require('vscode');
const { exec } = require('child_process');
const https = require('https');
const fs = require('fs');
const path = require('path');

function activate(context) {
    let installPyQt5 = vscode.commands.registerCommand('extension.installPyQt5', () => {
        exec('pip install PyQt5', (error, stdout, stderr) => {
            if (error) {
                vscode.window.showErrorMessage(`Error: ${stderr}`);
            } else {
                vscode.window.showInformationMessage('PyQt5 installed successfully!');
            }
        });
    });

    let downloadModule = vscode.commands.registerCommand('extension.downloadModule', () => {
        const url = 'https://github.com/tunnelrind/ksbanim/main/ksbanim.py';
        const dest = path.join(vscode.workspace.rootPath || '', 'ksbanim.py');

        https.get(url, (response) => {
            if (response.statusCode === 200) {
                const file = fs.createWriteStream(dest);
                response.pipe(file);
                file.on('finish', () => {
                    file.close();
                    vscode.window.showInformationMessage('ksbanim.py downloaded successfully!');
                });
            } else {
                vscode.window.showErrorMessage(`Failed to download ksbanim.py: ${response.statusCode}`);
            }
        }).on('error', (err) => {
            vscode.window.showErrorMessage(`Error: ${err.message}`);
        });
    });

    context.subscriptions.push(installPyQt5);
    context.subscriptions.push(downloadModule);
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};