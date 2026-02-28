# 🚦 RoadWatch Kerala - Traffic Violation Reporting System

A web application for reporting traffic violations in Kerala with AI-powered moderation to prevent spam and abuse.

# Install Python dependencies

The backend relies on `anthropic` which in turn depends on `httpx`.
If you run into startup errors mentioning ``Client.__init__() got an
unexpected keyword argument 'proxies'`` make sure you reinstall with the
latest dependencies (`pip install -r requirements.txt` will pull in
httpx>=0.30).  The code also includes a small compatibility shim in
``backend.py`` so that older `httpx` releases will still work.

```sh
pip install -r requirements.txt
```

### GET /api/reports
Get list of approved reports
- Query params: `?limit=10&offset=0`

### GET /api/reports/plate/{plate_number}
Get all reports for a specific vehicle

### GET /api/stats
Get overall statistics

### Authentication (optional)
The backend now supports Firebase authentication.  To register or update a
user, POST to `/api/auth/register` with a Bearer ID token in the
`Authorization` header.  Authenticated endpoints use the following routes:

```text
GET  /api/auth/profile      # return current user
GET  /api/auth/reports      # list reports submitted by current user
``` 

For convenience unauthenticated clients may still POST reports; they are
tracked by IP address and subject to duplicate prevention.

## 🎨 Customization Ideas

### Add User Authentication

### Add Email Notifications

### Add Image Storage (AWS S3 or Cloudinary)

## 🚀 Deployment Options

### Option 1: Railway (Easiest - Free Tier)

### Option 2: Vercel (Frontend) + Railway (Backend)

### Option 3: DigitalOcean App Platform

## 📱 Next Features to Build

**Week 1-2: Critical Path**
- [ ] User registration/login
- [ ] Real database (PostgreSQL or MongoDB)
- [ ] Image upload to cloud storage
- [ ] Email verification for reporters

**Week 3-4: Community Features**
- [ ] Vehicle safety score dashboard
- [ ] Heat map of violation hotspots
- [ ] Export reports for police
- [ ] User reputation system

**Week 5-6: Scale Features**
- [ ] Integrate with Vahan API (verify plate exists)
- [ ] Admin panel for manual review
- [ ] Push notifications for nearby violations
- [ ] WhatsApp integration for sharing


## 📞 What to Do Next

1. **Test it locally** - Make sure everything works
2. **Share with 5 friends** - Get them to submit real reports
3. **Post on r/Kerala** - "Testing a traffic violation reporting tool"
4. **Collect feedback** - What works? What's confusing?
5. **Iterate fast** - Add one feature per week based on feedback

## 🎯 Success Metrics

Track these to know if it's working:
- Reports submitted per day
- AI approval rate (should be 70-85%)
- Reports with photos (aim for >50%)
- Returning users (people who report multiple times)

---

**Built with Claude AI assistance** 🤖
