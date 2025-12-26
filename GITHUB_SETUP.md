# GitHub Deployment Setup Guide for Forewarned

## Step 1: Install Git for Windows

1. Download Git from: https://git-scm.com/download/win
2. Run the installer with these recommended settings:
   - ✅ Use Visual Studio Code as Git's default editor
   - ✅ Git from the command line and also from 3rd-party software
   - ✅ Use bundled OpenSSH
   - ✅ Use the OpenSSL library
   - ✅ Checkout Windows-style, commit Unix-style line endings
   - ✅ Use MinTTY
   - ✅ Default (fast-forward or merge)
   - ✅ Git Credential Manager
   - ✅ Enable file system caching

3. After installation, restart VS Code or your terminal

## Step 2: Configure Git (First Time Only)

Open a new terminal in VS Code and run:

```powershell
git config --global user.name "patchy"
git config --global user.email "cj.lewis1411@gmail.com"
```

## Step 3: Initialize Git Repository

```powershell
cd F:\Development\Homelab\Forewarned

# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Forewarned HA addon with weather and EOC monitoring"
```

## Step 4: Create GitHub Repository

1. Go to: https://github.com/new
2. Fill in:
   - Repository name: `forewarned` or `homeassistant-forewarned`
   - Description: "Home Assistant addon for weather alerting and EOC monitoring"
   - Public or Private: Your choice
   - ❌ Do NOT initialize with README (we already have one)
   - ❌ Do NOT add .gitignore (we already have one)
   - ❌ Do NOT add license yet

3. Click "Create repository"

## Step 5: Connect Local Repo to GitHub

GitHub will show you commands. Use these (replace YOUR-USERNAME):

```powershell
cd F:\Development\Homelab\Forewarned

# Add remote repository
git remote add origin https://github.com/YOUR-USERNAME/forewarned.git

# Rename branch to main (if needed)
git branch -M main

# Push code to GitHub
git push -u origin main
```

## Step 6: Create Repository Configuration for Home Assistant

Create a `repository.json` file (already exists or will be created):

This tells Home Assistant about your addon repository.

## Step 7: Add Repository to Home Assistant

1. Open Home Assistant
2. Go to: **Settings** → **Add-ons** → **Add-on Store**
3. Click the **3-dot menu (⋮)** in the top right
4. Select **Repositories**
5. Add your repository URL:
   ```
   https://github.com/YOUR-USERNAME/forewarned
   ```
6. Click **Add**
7. Close and reload the Add-on Store page
8. Find "Forewarned" in the store and click **Install**

## Step 8: Daily Development Workflow

### Making Changes:

```powershell
# 1. Make your code changes in VS Code
# 2. Test locally (optional)
python main.py

# 3. Stage your changes
git add .

# 4. Commit with a descriptive message
git commit -m "Added separate time tiles and date display"

# 5. Push to GitHub
git push
```

### Updating the Addon in Home Assistant:

**Option A: Restart Addon (for code changes)**
- Settings → Add-ons → Forewarned → **Restart**

**Option B: Update Addon (for version bumps)**
1. Update version in `config.json`:
   ```json
   {
     "version": "1.0.1"  // Increment this
   }
   ```
2. Commit and push
3. Settings → Add-ons → Forewarned → **Update**

**Option C: Rebuild Addon (for Dockerfile changes)**
- Settings → Add-ons → Forewarned → **Rebuild**

## Quick Reference Commands

```powershell
# Check status of your repository
git status

# See what changed
git diff

# View commit history
git log --oneline

# Create a new branch for features
git checkout -b feature-name

# Switch back to main
git checkout main

# Merge a feature branch
git merge feature-name

# Pull latest from GitHub
git pull

# Undo uncommitted changes
git checkout -- filename
```

## Troubleshooting

### "Git is not recognized"
- Restart VS Code or your terminal after installing Git
- Or manually add Git to PATH: `C:\Program Files\Git\cmd`

### "Permission denied (publickey)"
- Use HTTPS instead of SSH for GitHub URLs
- Or set up SSH keys: https://docs.github.com/en/authentication/connecting-to-github-with-ssh

### "Changes not appearing in Home Assistant"
- Make sure to restart/rebuild the addon after pushing
- Check addon logs for errors
- Verify version number was updated (if using Update button)

## Version Bumping Strategy

Use semantic versioning (MAJOR.MINOR.PATCH):

- **PATCH** (1.0.1): Bug fixes, minor changes
- **MINOR** (1.1.0): New features, backward compatible
- **MAJOR** (2.0.0): Breaking changes

Update in `config.json` and `CHANGELOG.md`

## Next Steps

Once your repository is on GitHub:

1. Add a LICENSE file (MIT recommended for open source)
2. Add screenshots to README.md
3. Create GitHub releases for major versions
4. Consider adding GitHub Actions for automated testing
5. Submit to Home Assistant Community Add-ons (optional)

---

**Need Help?**
- GitHub Docs: https://docs.github.com
- Home Assistant Addon Development: https://developers.home-assistant.io/docs/add-ons
