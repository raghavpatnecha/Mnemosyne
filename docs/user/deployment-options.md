# Mnemosyne Deployment Options & Data Persistence

## Understanding Docker Volumes

### What `driver: local` Means

**`driver: local`** = Data stored on the **Docker host's disk** (your production server)

```yaml
volumes:
  lightrag_data:
    driver: local  # ← Data persists on server disk
```

**Location**: `/var/lib/docker/volumes/mnemosyne_lightrag_data/`

### Data Persistence Behavior

| Scenario | Data Persists? |
|----------|----------------|
| Container restart | ✅ YES |
| Container rebuild | ✅ YES |
| Code update | ✅ YES |
| Server reboot | ✅ YES |
| Volume deleted | ❌ NO |
| Server replacement | ❌ NO (need backup) |
| Disk failure | ❌ NO (need backup) |

---

## Deployment Scenarios

### 1. **Single Server Deployment** (Current Setup)

**Best for**: Small to medium deployments (1-10K users)

```yaml
volumes:
  postgres_data:
    driver: local
  lightrag_data:
    driver: local
```

**Pros**:
- ✅ Simple setup
- ✅ No external dependencies
- ✅ Data persists on server

**Cons**:
- ⚠️ Single point of failure
- ⚠️ Manual backups needed
- ⚠️ Can't scale horizontally

**Recommendation**: Use with automated backups (already configured!)

---

### 2. **Cloud Provider Managed Volumes**

**Best for**: Production apps with high availability needs

#### AWS (Elastic Block Store)

```yaml
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: "nfs"
      o: "addr=<EFS-DNS>,nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2"
      device: ":/"

  # OR use Docker Volume Plugin
  lightrag_data:
    driver: rexray/ebs
    driver_opts:
      size: 20
      volumetype: gp3
```

**Setup**:
```bash
# Install Docker EBS plugin
docker plugin install rexray/ebs

# Volumes automatically attach to EC2 instances
```

#### Google Cloud (Persistent Disks)

```yaml
volumes:
  lightrag_data:
    driver: gcplogs
    driver_opts:
      gcp-project: "your-project"
      size: "20GB"
```

#### DigitalOcean (Block Storage)

```yaml
volumes:
  postgres_data:
    external: true
    name: mnemosyne-postgres-volume  # Created via DO dashboard
```

**Pros**:
- ✅ Automatic backups/snapshots
- ✅ High availability
- ✅ Can attach to different servers

**Cons**:
- ⚠️ More complex setup
- ⚠️ Additional cost

---

### 3. **Network File Systems (NFS/GlusterFS)**

**Best for**: Multi-server deployments

```yaml
volumes:
  lightrag_data:
    driver: local
    driver_opts:
      type: nfs
      o: addr=192.168.1.100,nolock,soft,rw
      device: ":/mnt/lightrag"
```

**Setup**:
```bash
# On NFS server
sudo apt-get install nfs-kernel-server
sudo mkdir -p /mnt/lightrag
echo "/mnt/lightrag *(rw,sync,no_subtree_check)" >> /etc/exports
sudo exportfs -a

# On Docker hosts (automatic via driver_opts)
```

**Pros**:
- ✅ Shared across multiple servers
- ✅ Centralized storage

**Cons**:
- ⚠️ Network dependency
- ⚠️ Potential performance impact
- ⚠️ Single point of failure (NFS server)

---

### 4. **Object Storage (S3-compatible)**

**Best for**: Large files, uploads, backups

```yaml
# Not for PostgreSQL/LightRAG (need filesystem)
# Good for uploads and backups only
```

**Configuration in `.env.production`**:
```bash
# Uploads to S3
USE_OBJECT_STORAGE=true
S3_BUCKET=mnemosyne-uploads
S3_REGION=us-east-1
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key

# Backups to S3
BACKUP_S3_BUCKET=mnemosyne-backups
```

**Code changes needed**: Update `backend/storage/` to use boto3

**Pros**:
- ✅ Unlimited storage
- ✅ High durability (99.999999999%)
- ✅ CDN integration

**Cons**:
- ⚠️ Not suitable for databases
- ⚠️ Requires code changes

---

## Recommended Setups by Scale

### **Small (< 1K users)**
```yaml
# Current setup: local volumes + daily backups
volumes:
  postgres_data:
    driver: local
  lightrag_data:
    driver: local

# Backups: Daily to local disk + weekly to S3
```

**Cost**: ~$24/month (server only)

---

### **Medium (1K - 10K users)**
```yaml
# Cloud managed volumes + automated backups
volumes:
  postgres_data:
    driver: rexray/ebs  # AWS
    driver_opts:
      size: 50
      volumetype: gp3

  lightrag_data:
    driver: rexray/ebs
    driver_opts:
      size: 20
      volumetype: gp3

# Uploads: S3
# Backups: Daily snapshots
```

**Cost**: ~$100-200/month
- Server: $40
- EBS volumes: $15
- S3: $10
- Snapshots: $20
- Data transfer: $15

---

### **Large (10K+ users)**
```yaml
# Multi-region with replication
- Primary region: RDS + managed volumes
- Replica region: Read replicas
- CDN: CloudFront for uploads
- Backups: Multi-region snapshots

# Replace local PostgreSQL with managed RDS
DATABASE_URL=postgresql://user:pass@rds.amazonaws.com/db
```

**Cost**: ~$500+/month
- RDS (multi-AZ): $200
- EBS/EFS: $50
- S3 + CloudFront: $100
- Load balancer: $20
- Backups: $50
- Servers: $80

---

## Backup Strategies

### **Included in Production Config**

1. **Daily Automated Backups**
   ```bash
   # Runs every 24 hours
   - PostgreSQL (embeddings + metadata)
   - LightRAG (knowledge graph)
   - Uploads (original files)
   ```

2. **Retention**: 7 days (configurable)

3. **Optional S3 Upload**:
   ```bash
   BACKUP_S3_BUCKET=mnemosyne-backups
   # Automatically uploads to S3 after backup
   ```

### **Manual Backup**

```bash
# Complete backup
docker-compose -f docker-compose.prod.yml exec backup /usr/local/bin/backup

# View backups
docker-compose -f docker-compose.prod.yml exec backup ls -lh /backups/

# Restore from backup
docker-compose -f docker-compose.prod.yml exec backup /app/scripts/restore.sh 20240117_120000
```

---

## Migration Between Servers

### **Moving to a New Server**

1. **Create backup on old server**:
   ```bash
   ./scripts/backup-complete.sh
   ```

2. **Copy backups to new server**:
   ```bash
   # From old server
   scp -r /var/lib/docker/volumes/mnemosyne_postgres_backups/ \
       user@new-server:/tmp/backups/
   ```

3. **Restore on new server**:
   ```bash
   # On new server
   ./scripts/deploy.sh
   docker-compose -f docker-compose.prod.yml exec backup \
       /app/scripts/restore.sh 20240117_120000
   ```

---

## Disaster Recovery

### **Backup Checklist**

- [x] PostgreSQL: Automated daily
- [x] LightRAG: Automated daily
- [x] Uploads: Automated daily
- [ ] Off-site backups (S3): Configure `BACKUP_S3_BUCKET`
- [ ] Test restores: Monthly
- [ ] Monitoring: Set up alerts

### **Recovery Time Objectives (RTO)**

| Component | RTO | RPO |
|-----------|-----|-----|
| Application | 5 min | 0 (stateless) |
| PostgreSQL | 15 min | 24h (daily backup) |
| LightRAG | 10 min | 24h (daily backup) |
| Uploads | 20 min | 24h (daily backup) |

### **To Improve RPO** (Recovery Point Objective)

1. **Continuous Backup** (PostgreSQL WAL):
   ```yaml
   # Enable Write-Ahead Logging
   POSTGRES_WAL_LEVEL=replica
   POSTGRES_ARCHIVE_MODE=on
   POSTGRES_ARCHIVE_COMMAND='cp %p /backups/wal/%f'
   ```

2. **Increase Backup Frequency**:
   ```yaml
   # Hourly backups instead of daily
   command: -c "while true; do /usr/local/bin/backup; sleep 3600; done"
   ```

---

## Summary

### **Current Production Setup** (Good for most cases)

✅ **What you have**:
- Local volumes (data persists on server)
- Daily automated backups
- 7-day retention
- Optional S3 upload

✅ **What's protected**:
- Container restarts ✅
- Code updates ✅
- Server reboots ✅

⚠️ **What's NOT protected** (without additional config):
- Server disk failure ⚠️ (need S3 backups)
- Accidental deletion ⚠️ (backups help)
- Multi-server scaling ⚠️ (need network volumes)

### **Quick Wins**

1. **Enable S3 backups**:
   ```bash
   # In .env.production
   BACKUP_S3_BUCKET=your-bucket-name
   ```

2. **Test restore monthly**:
   ```bash
   ./scripts/restore.sh $(date +%Y%m%d)
   ```

3. **Monitor disk space**:
   ```bash
   df -h
   docker system df
   ```

---

**Bottom line**: Your current setup is **production-ready** for single-server deployments. Data persists on the server disk and is backed up daily. For higher availability, consider cloud-managed volumes or NFS.
