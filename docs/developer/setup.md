# Setting Up Reference Repositories

This guide will help you add SurfSense and RAG-Anything as git submodules to the Mnemosyne repository.

## Why Submodules?

Git submodules allow us to:
- ✅ Track reference implementations within our repo
- ✅ Keep them separate and version-controlled
- ✅ Easy to update when they change upstream
- ✅ Clean separation between our code and references

## Quick Setup (Automated)

### Option 1: Run the Setup Script

```bash
# Navigate to repository root
cd /home/user/Mnemosyne

# Ensure you're on the correct branch
git checkout claude/check-mnemosyne-repo-01BswSWffoPM15U89RrZEtNB

# Run the setup script
./setup_references.sh

# Commit the submodules
git add .gitmodules references/
git commit -m "chore: add SurfSense and RAG-Anything as submodules"
git push
```

The script will:
1. Add SurfSense as a submodule at `references/surfsense/`
2. Add RAG-Anything as a submodule at `references/rag-anything/`
3. Initialize and update both submodules

---

## Manual Setup (Step-by-Step)

### Option 2: Add Submodules Manually

If the script doesn't work, add them manually:

```bash
# Navigate to repository root
cd /home/user/Mnemosyne

# Ensure you're on the correct branch
git checkout claude/check-mnemosyne-repo-01BswSWffoPM15U89RrZEtNB

# Add SurfSense as submodule
git submodule add https://github.com/DAMG7245/surf-sense.git references/surfsense

# Add RAG-Anything as submodule
git submodule add https://github.com/ictnlp/RAG-Anything.git references/rag-anything

# Initialize and update submodules
git submodule init
git submodule update

# Commit the changes
git add .gitmodules references/
git commit -m "chore: add SurfSense and RAG-Anything as submodules"
git push
```

---

## Troubleshooting

### Authentication Issues

If you get an error like:
```
fatal: could not read Username for 'https://github.com'
```

**Solution 1: Use GitHub CLI**
```bash
# Authenticate with GitHub
gh auth login

# Then run the setup script or manual commands
```

**Solution 2: Use SSH URLs**
```bash
# Instead of HTTPS URLs, use SSH
git submodule add git@github.com:DAMG7245/surf-sense.git references/surfsense
git submodule add git@github.com:ictnlp/RAG-Anything.git references/rag-anything
```

**Solution 3: Use Personal Access Token**
```bash
# Set git credential helper
git config --global credential.helper cache

# When prompted, use your GitHub username and Personal Access Token
# Create token at: https://github.com/settings/tokens
```

### Submodule Already Exists

If you see:
```
A git directory for 'references/surfsense' is found locally
```

**Solution:**
```bash
# Remove the existing directory
rm -rf references/surfsense references/rag-anything

# Remove from git index
git rm --cached references/surfsense references/rag-anything 2>/dev/null || true

# Try adding again
git submodule add https://github.com/DAMG7245/surf-sense.git references/surfsense
git submodule add https://github.com/ictnlp/RAG-Anything.git references/rag-anything
```

---

## Verifying the Setup

After adding submodules, verify they're set up correctly:

```bash
# Check submodule status
git submodule status

# Should show:
#  <commit-hash> references/rag-anything (v1.0.0)
#  <commit-hash> references/surfsense (main)

# Check .gitmodules file
cat .gitmodules

# Should contain:
# [submodule "references/surfsense"]
#     path = references/surfsense
#     url = https://github.com/DAMG7245/surf-sense.git
# [submodule "references/rag-anything"]
#     path = references/rag-anything
#     url = https://github.com/ictnlp/RAG-Anything.git

# Verify files exist
ls -la references/surfsense/
ls -la references/rag-anything/
```

---

## Working with Submodules

### Cloning the Repo with Submodules (For Others)

When someone else clones your repo, they need to initialize submodules:

```bash
# Clone the main repo
git clone <your-repo-url>

# Initialize and update submodules
git submodule init
git submodule update

# Or do it all at once
git clone --recurse-submodules <your-repo-url>
```

### Updating Submodules

To pull the latest changes from SurfSense/RAG-Anything:

```bash
# Update all submodules to latest
git submodule update --remote

# Or update specific submodule
cd references/surfsense
git pull origin main
cd ../..

# Commit the updated submodule reference
git add references/surfsense
git commit -m "chore: update SurfSense submodule"
```

### Removing a Submodule

If you need to remove a submodule:

```bash
# Remove from .gitmodules
git submodule deinit -f references/surfsense

# Remove from .git/modules/
rm -rf .git/modules/references/surfsense

# Remove from working tree
git rm -f references/surfsense

# Commit
git commit -m "chore: remove SurfSense submodule"
```

---

## What Files Will Be Added

After adding submodules, your repository will have:

```
.gitmodules                    # Submodule configuration (tracked)
references/
  ├── README.md                # Study guide (tracked)
  ├── surfsense/               # SurfSense code (submodule)
  │   ├── surfsense_backend/
  │   ├── surfsense_frontend/
  │   └── ...
  └── rag-anything/            # RAG-Anything code (submodule)
      ├── lightrag/
      ├── multimodal/
      └── ...
```

**Important:** The `.gitignore` is configured to:
- ✅ Track `.gitmodules` and `references/README.md`
- ❌ Ignore the submodule contents (they're tracked by git submodules)

---

## Next Steps After Setup

Once submodules are added and committed:

1. **Study Key Files**
   ```bash
   # See what to study
   cat references/README.md

   # SurfSense file processors
   cat references/surfsense/surfsense_backend/app/tasks/document_processors/file_processors.py

   # SurfSense LLM service
   cat references/surfsense/surfsense_backend/app/services/llm_service.py
   ```

2. **Start Phase 2 Development**
   ```bash
   # Read the roadmap
   cat PHASE_2_ROADMAP.md

   # Choose Week 6 starting point:
   # - Testing infrastructure
   # - File format support
   # - LiteLLM integration
   ```

3. **Tell Claude Which Feature to Implement**
   - I'm ready to start coding once you choose your priority!

---

## Quick Reference

### Common Commands

```bash
# Add submodule
git submodule add <url> <path>

# Initialize submodules (after cloning)
git submodule init
git submodule update

# Update submodules to latest
git submodule update --remote

# Check submodule status
git submodule status

# Foreach command (run in all submodules)
git submodule foreach git pull origin main
```

### URLs

- **SurfSense:** https://github.com/DAMG7245/surf-sense
- **RAG-Anything:** https://github.com/ictnlp/RAG-Anything

---

## Support

If you encounter issues:

1. Check this troubleshooting guide
2. Verify git is configured: `git config --list`
3. Ensure GitHub authentication works: `gh auth status` or `ssh -T git@github.com`
4. Ask Claude for help with specific error messages

---

**Ready to set up the references? Run `./setup_references.sh` to get started!**
