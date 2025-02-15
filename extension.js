const vscode = require('vscode');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

function customLog(msg) {
	console.log(" > ksbanim " + msg)
}

function activate(context) {
	customLog('activating ksbanim extension');
	
	let downloadFileDisposable = vscode.commands.registerCommand('ksbanim.downloadFile', function () {
		return downloadKsbanim();
	});

	let downloadQtDisposable = vscode.commands.registerCommand('ksbanim.downloadQt', function () {
		return downloadQt();
	});
	
	context.subscriptions.push(downloadFileDisposable);
	context.subscriptions.push(downloadQtDisposable);

	const treeDataProvider = new MyTreeDataProvider();
	vscode.window.registerTreeDataProvider('ksbanim.myCustomView', treeDataProvider);
}

async function downloadKsbanim() {
	return vscode.window.withProgress({
		location: vscode.ProgressLocation.Notification,
		title: "Downloading ksbanim.py",
		cancellable: false
	}, (progress) => {
		return new Promise((resolve, reject) => {
			const url = 'https://raw.githubusercontent.com/tunnelrind/ksbanim/main/ksbanim.py';
			const workspaceFolders = vscode.workspace.workspaceFolders;
			
			if (!workspaceFolders) {
				vscode.window.showErrorMessage('No workspace folder is open.');
				reject('No workspace folder is open.');
				return;
			}
			
			const filePath = path.join(workspaceFolders[0].uri.fsPath, 'ksbanim.py');
			
			https.get(url, (response) => {
				if (response.statusCode !== 200) {
					vscode.window.showErrorMessage(`Failed to download file: ${response.statusCode}`);
					reject(`Failed to download file: ${response.statusCode}`);
					return;
				}
				
				const file = fs.createWriteStream(filePath);
				response.pipe(file);
				
				file.on('finish', () => {
					file.close();
					vscode.window.showInformationMessage('ksbanim.py downloaded successfully!');
					console.log('ksbanim.py downloaded successfully!');
					resolve();
				});
			}).on('error', (error) => {
				vscode.window.showErrorMessage(`Error downloading file: ${error.message}`);
				reject(error);
			});
		});
	});
}

async function downloadQt() {	
	return vscode.window.withProgress({
		location: vscode.ProgressLocation.Notification,
		title: "Downloading PyQt5. Please wait.",
		cancellable: false
	}, (progress) => {
		return new Promise((resolve, reject) => {
			const command = 'pip install PyQt5 --quiet --disable-pip-version-check';
			const child = exec(command);
			
			let progressInterval = setInterval(() => {
				progress.report({ message: 'Downloading...' });
			}, 1000); // Update progress every second
			
			child.stdout.on('data', (data) => {
				// You can add custom logic here if needed
			});
			
			child.on('close', (code) => {
				clearInterval(progressInterval);
				if (code === 0) {
					vscode.window.showInformationMessage('PyQt5 downloaded and installed successfully.');
					resolve();
				} else {
					vscode.window.showErrorMessage('Failed to download PyQt5.');
					reject(new Error('Failed to download PyQt5.'));
				}
			});
			
			child.on('error', (error) => {
				clearInterval(progressInterval);
				vscode.window.showErrorMessage(`Error: ${error.message}`);
				reject(error);
			});
		});
	});
}

class MyTreeDataProvider {
	getTreeItem(element) {
		return element;
	}
	
	getChildren(element) {
		if (!element) {
			return [
				new MyTreeItem('ksbanim.py', 'ksbanim.downloadFile'),
				new MyTreeItem('PyQt5', 'ksbanim.downloadQt') // Add this line
			];
		}
		return [];
	}
}

class MyTreeItem extends vscode.TreeItem {
	constructor(label, command) {
		super(label);
		this.command = {
			command: command,
			title: '',
			arguments: []
		};
		this.iconPath = new vscode.ThemeIcon('cloud-download');
	}
}

function deactivate() {}

module.exports = {
	activate,
	deactivate
};