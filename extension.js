const vscode = require('vscode');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { exec, execFile} = require('child_process');
const os = require('os');

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
	
	let downloadPythonExtensionDisposable = vscode.commands.registerCommand('ksbanim.downloadPythonExtension', async function () {
		await downloadPythonExtension();
	});
	
	context.subscriptions.push(downloadFileDisposable);
	context.subscriptions.push(downloadQtDisposable);
	context.subscriptions.push(downloadPythonExtensionDisposable)
	
	const treeDataProvider = new MyTreeDataProvider();
	vscode.window.registerTreeDataProvider('ksbanim.myCustomView', treeDataProvider);
}

async function downloadPythonExtension() {
	const pythonExtensionId = 'ms-python.python';
	
	// Check if the Python extension is already installed
	const extension = vscode.extensions.getExtension(pythonExtensionId);
	if (extension) {
		vscode.window.showInformationMessage('Python extension is already installed.');
		return;
	}
	
	// Show progress dialog while installing the extension
	await vscode.window.withProgress({
		location: vscode.ProgressLocation.Notification,
		title: "Installing Python extension. Please wait.",
		cancellable: false
	}, async (progress) => {
		return new Promise((resolve, reject) => {
			vscode.commands.executeCommand('workbench.extensions.installExtension', pythonExtensionId)
			.then(() => {
				vscode.window.showInformationMessage('Python extension installed successfully.');
				resolve();
			})
			.catch((error) => {
				vscode.window.showErrorMessage(`Failed to install Python extension: ${error.message}`);
				reject(error);
			});
		});
	});
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

async function checkQtInstalled() {
	return new Promise((resolve) => {
		exec('pip show PyQt5', (error, stdout, stderr) => {
			if (error) {
				resolve(false);
			} else {
				resolve(true);
			}
		});
	});
}

async function downloadQt() {
	const isQtInstalled = await checkQtInstalled();
	if (isQtInstalled) {
		vscode.window.showInformationMessage('PyQt5 is already installed on your system.');
		return;
	}
	
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
				new MyTreeItem('python extension', 'ksbanim.downloadPythonExtension'),
				new MyTreeItem('PyQt5', 'ksbanim.downloadQt'),
				new MyTreeItem('ksbanim.py', 'ksbanim.downloadFile'),
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