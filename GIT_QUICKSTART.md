# Quick Reference: Git & GitHub Workflow

## 🚀 One-Time Setup

### 1. Install Git
Download: https://git-scm.com/download/win

### 2. Run Setup Script
```powershell
.\setup-git.ps1
```

### 3. Update repository.json
Edit `repository.json` and replace:
- `YOUR-USERNAME` with your GitHub username
- `Your Name <your@email.com>` with your info

---

## 📝 Daily Workflow

### Make Changes & Push
```powershell
# After editing files...
git add .
git commit -m "Description of what you changed"
git push
```

### Update in Home Assistant
**For code changes:** Just restart the addon
**For version changes:** Update addon in HA Store

---

## 🔧 Common Commands

```powershell
# Check what changed
git status

# View differences
git diff

# See commit history
git log --oneline

# Undo uncommitted changes to a file
git checkout -- filename

# Pull latest from GitHub
git pull
```

---

## 📦 Version Bumping

1. Edit `config.json`:
   ```json
   "version": "1.0.1"  // Increment this
   ```

2. Update `CHANGELOG.md`

3. Commit and push:
   ```powershell
   git add .
   git commit -m "Bump version to 1.0.1"
   git push
   ```

4. Update addon in Home Assistant

---

## 🏠 Home Assistant Repository URL

After pushing to GitHub, add this to Home Assistant:

```
Settings → Add-ons → Add-on Store → ⋮ → Repositories
Add: https://github.com/YOUR-USERNAME/forewarned
```

---

## 🆘 Troubleshooting

**Git not recognized?**
- Restart VS Code after installing Git

**Authentication failed?**
- GitHub removed password auth
- Use Personal Access Token or GitHub CLI
- Generate token: https://github.com/settings/tokens

**Changes not showing in HA?**
- Restart the addon
- Or rebuild if Dockerfile changed
- Check addon logs for errors

---

## 📚 Full Documentation

See `GITHUB_SETUP.md` for detailed instructions
