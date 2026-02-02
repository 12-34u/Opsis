# 🔨 Build & Deploy Guide - Opsis Code Editor

## 📋 Prerequisites

### Required Software
- **Node.js** 16.x or higher ([Download](https://nodejs.org/))
- **npm** (comes with Node.js)
- **Git** (optional, for version control)

### Optional (for code execution)
- **Python** 3.x ([Download](https://www.python.org/downloads/))
- **Java JDK** 8+ ([Download](https://www.oracle.com/java/technologies/downloads/))

### Verify Installation
```bash
node --version   # Should show v16.x.x or higher
npm --version    # Should show 8.x.x or higher
python --version # Optional: For Python code execution
javac --version  # Optional: For Java code execution
```

## 🚀 Quick Start (Development)

### 1. Install Dependencies
```bash
cd d:\Desktop\Opsis\frontend\my-app
npm install
```

This will install:
- Electron and Electron Builder
- React and React DOM
- Vite and plugins
- Monaco Editor
- All development dependencies

### 2. Run Development Server
```bash
npm run dev
```

This will:
- Start Vite dev server on http://localhost:5173
- Build Electron main and preload scripts
- Auto-open Electron window (desktop app)
- Enable hot module reload (HMR)

### 3. Access the Application

**Option A: Electron Desktop App**
- Window opens automatically after `npm run dev`
- Full desktop application experience
- File system access for open/save operations

**Option B: Web Browser**
- Navigate to http://localhost:5173
- Good for testing UI changes
- Limited file system access (security restrictions)

## 🏗️ Building for Production

### Build Desktop Application

```bash
npm run electron:build
```

This will:
1. Build the React app with Vite
2. Bundle Electron main and preload scripts
3. Package everything with Electron Builder
4. Create platform-specific installers

### Output Location
```
frontend/my-app/release/
├── Opsis Code Editor Setup 1.0.0.exe    # Windows installer (NSIS)
├── Opsis Code Editor 1.0.0.dmg          # macOS disk image
└── Opsis-Code-Editor-1.0.0.AppImage     # Linux AppImage
```

### Platform-Specific Builds

#### Windows Only
```bash
npm run electron:build -- --win
```
Creates: `.exe` installer

#### macOS Only (requires macOS)
```bash
npm run electron:build -- --mac
```
Creates: `.dmg` disk image

#### Linux Only
```bash
npm run electron:build -- --linux
```
Creates: `.AppImage` file

## 📦 Build Configuration

### Customizing Build (package.json)

```json
"build": {
  "appId": "com.opsis.codeeditor",
  "productName": "Opsis Code Editor",
  "directories": {
    "output": "release"
  },
  "files": [
    "dist/**/*",
    "electron/**/*"
  ],
  "win": {
    "target": "nsis",
    "icon": "public/icon.png"
  },
  "mac": {
    "target": "dmg",
    "icon": "public/icon.png"
  },
  "linux": {
    "target": "AppImage",
    "icon": "public/icon.png"
  }
}
```

### Adding an Icon

1. Create a 512x512 PNG icon
2. Save as `public/icon.png`
3. For Windows: Convert to `.ico` (optional)
4. For macOS: Convert to `.icns` (optional)
5. Rebuild the application

## 🔧 Development Scripts

### Available Commands

```bash
# Development
npm run dev              # Start dev server + Electron
npm run electron:start   # Launch Electron (requires dev server running)

# Building
npm run build            # Build React app only
npm run electron:build   # Build complete desktop app

# Utilities
npm run lint             # Run ESLint
npm run preview          # Preview production build
```

## 🐛 Troubleshooting Build Issues

### Issue: "electron-builder not found"
```bash
npm install electron-builder --save-dev
```

### Issue: "Module not found"
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Issue: Build fails on Windows
```bash
# Run as administrator
# Or install windows-build-tools
npm install --global windows-build-tools
```

### Issue: Build fails on macOS
```bash
# Install Xcode Command Line Tools
xcode-select --install
```

### Issue: Build fails on Linux
```bash
# Install required dependencies
sudo apt-get install -y libgtk-3-dev libnotify-dev libgconf-2-4 libnss3 libxss1 libasound2
```

## 📁 Project Structure After Build

```
my-app/
├── node_modules/         # Dependencies (don't commit)
├── electron/
│   ├── main.js          # Main process source
│   └── preload.js       # Preload script source
├── src/                 # React source code
├── public/              # Static assets
├── dist/                # Built React app (generated)
├── dist-electron/       # Built Electron files (generated)
├── release/             # Packaged apps (generated)
│   └── Opsis Code Editor Setup 1.0.0.exe
└── package.json
```

## 🚢 Deployment Options

### 1. Local Installation (Recommended)
- Build the app: `npm run electron:build`
- Distribute the installer from `release/` folder
- Users install like any desktop app

### 2. Portable Version
- No installation required
- Extract and run directly
- Configure in electron-builder:
```json
"win": {
  "target": [
    {
      "target": "portable",
      "arch": ["x64"]
    }
  ]
}
```

### 3. Auto-Update
- Integrate electron-updater
- Host releases on GitHub or server
- App checks for updates automatically

### 4. Web Version (Limited)
- Build with `npm run build`
- Deploy `dist/` folder to web server
- Note: File system operations won't work

## 🔐 Code Signing (Optional)

### Windows Code Signing
```json
"win": {
  "certificateFile": "path/to/cert.pfx",
  "certificatePassword": "password"
}
```

### macOS Code Signing
```json
"mac": {
  "identity": "Developer ID Application: Your Name"
}
```

## 📊 Build Optimization

### Reduce Bundle Size
1. Remove unused dependencies
2. Enable tree-shaking (already configured)
3. Minimize Monaco Editor languages:
```javascript
// In vite.config.js
monacoEditorPlugin({
  languages: ['javascript', 'python', 'java']
})
```

### Speed Up Builds
1. Use parallel builds
2. Enable caching
3. Exclude unnecessary files

## 🧪 Testing Before Release

### Pre-Build Checklist
- [ ] Test all features in development mode
- [ ] Verify file operations work
- [ ] Test code execution for all languages
- [ ] Check theme switching
- [ ] Test on target platforms
- [ ] Update version in package.json
- [ ] Update README with changes
- [ ] Review error handling

### Post-Build Testing
- [ ] Install the built application
- [ ] Test first run experience
- [ ] Verify file operations
- [ ] Test code execution
- [ ] Check for crashes
- [ ] Verify uninstall process

## 📝 Version Management

### Updating Version Number

Edit `package.json`:
```json
{
  "version": "1.0.1"  // Increment version
}
```

### Semantic Versioning
- **1.0.0** → Major release
- **1.1.0** → Minor update (new features)
- **1.0.1** → Patch (bug fixes)

## 🌐 Distribution Channels

### 1. Direct Download
- Host installer on your website
- Provide download links
- Include installation instructions

### 2. GitHub Releases
- Create releases on GitHub
- Upload installers
- Auto-update integration available

### 3. Microsoft Store (Windows)
- Submit to Windows Store
- Reach wider audience
- Automatic updates

### 4. Mac App Store
- Submit to Apple App Store
- Requires Apple Developer account
- Additional requirements

### 5. Snap Store (Linux)
- Package as Snap
- Available in Snap Store
- Cross-distribution support

## 💰 Monetization (Optional)

### Free Open Source
- MIT License
- Host on GitHub
- Build community

### Freemium Model
- Basic version free
- Premium features paid
- Subscription or one-time

### Enterprise License
- Commercial license
- Support packages
- Custom features

## 📈 Analytics (Optional)

### Track Usage
```bash
npm install electron-google-analytics
```

### Error Reporting
```bash
npm install @sentry/electron
```

## 🔄 CI/CD Setup (Advanced)

### GitHub Actions Example
```yaml
name: Build and Release
on:
  push:
    tags:
      - 'v*'
jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [windows-latest, macos-latest, ubuntu-latest]
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
      - run: npm install
      - run: npm run electron:build
```

## ✅ Final Checklist

Before releasing:
- [x] Application built successfully
- [x] Tested on target platform
- [x] Version number updated
- [x] Documentation complete
- [x] Screenshots prepared
- [x] Release notes written
- [ ] Code signed (optional)
- [ ] Tested installation process
- [ ] Tested uninstallation
- [ ] Performance optimized

## 🎉 Success!

Your Opsis Code Editor is now ready for distribution!

### Quick Build Command
```bash
npm run electron:build
```

### Find Your Installer
```
frontend/my-app/release/Opsis Code Editor Setup 1.0.0.exe
```

### Next Steps
1. Test the installer
2. Share with users
3. Gather feedback
4. Plan updates

---

**Happy Building! 🚀**

*For questions, check PROJECT_SUMMARY.md or README_OPSIS.md*
