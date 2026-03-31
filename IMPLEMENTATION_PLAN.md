# 🚀 Mall Navigator – Implementation Plan for Future Improvements

**Last Updated**: March 31, 2026  
**Current Status**: Functional Streamlit MVP with Dijkstra + A* comparison  
**Deployment**: Streamlit Community Cloud

---

## 📋 Executive Summary

The **Mall Navigator** is a well-structured A-Level project that successfully demonstrates indoor pathfinding with educational algorithm comparison. The implementation is clean, modular, and deployable. This plan outlines strategic improvements across **5 phases** (Quick Wins → Advanced Features → Production Hardening).

---

## 🎯 Phase 1: Quick Wins (1–2 weeks) – Foundation Improvements

### 1.1 Code Quality & Maintainability
**Priority**: HIGH | **Effort**: 2 days | **Impact**: Reduced bugs, easier development

**Tasks**:
- [ ] Add comprehensive type hints to all `components/` modules (currently missing)
- [ ] Create a `config.py` for constants (FLOORS, INTER_FLOOR_EDGES, colors hardcoded in `map_view.py`)
- [ ] Extract magic numbers to named constants (e.g., `WAYPOINT_RADIUS = 5`, `PATH_LINE_WIDTH = 5`)
- [ ] Add unit tests for core algorithms:
  - [ ] Test Dijkstra with disconnected graphs
  - [ ] Test A* admissibility property
  - [ ] Test multi-floor path reconstruction
  - [ ] Test product search (partial match, exact match, case-insensitive)
- [ ] Document graph JSON schema in `data/graphs/README.md`

**Benefits**: 
- Catch edge cases early
- Easier to refactor later
- Better IDE support

---

### 1.2 User Experience Polish
**Priority**: HIGH | **Effort**: 3 days | **Impact**: Better usability

**Tasks**:
- [ ] Add keyboard shortcuts (e.g., `Alt+N` for Navigate, `Alt+A` for Add Product)
- [ ] Improve error messages:
  - [ ] "Path not found" → explain why (disconnected graph? outside service area?)
  - [ ] GPS errors → show troubleshooting steps
- [ ] Add a "Recent Searches" cache (SQLite or in-session JSON)
- [ ] Highlight the selected start/end node with node ID labels on map
- [ ] Add "Clear Selection" button for quick reset
- [ ] Show estimated distances in metres (integrate `px_per_metre` scale better)
- [ ] Dark mode toggle (Streamlit theme customization)

**Files to Modify**:
- `app.py` (sidebar + main logic)
- `components/map_view.py` (node labels)
- `components/directions_panel.py` (error messages)

---

### 1.3 Performance Optimization
**Priority**: MEDIUM | **Effort**: 2 days | **Impact**: Faster app load

**Tasks**:
- [ ] **Lazy-load graphs**: Only load the current floor's graph, not all three
- [ ] **Cache combined graphs**: Pre-compute the multi-floor graph once instead of every pathfinding call
- [ ] **Profile Streamlit rerun**: Identify slow widgets (likely map rendering or search)
- [ ] **Optimize Pillow rendering**: Pre-render base map layers (floor plan → PIL cache)
- [ ] **Reduce image size**: Compress PNGs in `data/maps/` (target < 200KB each)

**Expected Improvement**: Load time 2–3 seconds → < 1 second

---

## 🔧 Phase 2: Feature Enhancement (2–3 weeks) – Core Functionality Expansion

### 2.1 Real-World Routing Enhancements
**Priority**: HIGH | **Effort**: 1 week | **Impact**: More practical navigation

**Tasks**:
- [ ] **Add accessibility mode**: Mark stairs/escalators as optional, prefer ramps/lifts
  - [ ] Update graph JSON to include node attributes (e.g., `"floor": 1, "accessible": true`)
  - [ ] Filter paths in Dijkstra/A* based on accessibility filter
- [ ] **Estimated walking time**: Calculate based on path length + complexity (stairs = slower)
  - [ ] Add `walking_time_seconds()` utility function
- [ ] **Add opening hours**: Extend `products.json` to include shop hours; warn if closed
- [ ] **Alternative routes**: Show top 3 paths (Yen's algorithm or variants)
  - [ ] Add modal to compare cost/distance of alternatives

**Files to Create**:
- [ ] `algorithms/yen_ksp.py` – K-shortest paths implementation

---

### 2.2 Enhanced Product Management
**Priority**: MEDIUM | **Effort**: 4 days | **Impact**: Richer data, better search

**Tasks**:
- [ ] **Migrate to SQLite** instead of JSON (for larger datasets, queries)
  - [ ] Create `ProductStore` class (abstract from file format)
  - [ ] Add migrations script
- [ ] **Bulk import CSV/Excel**: Allow mall operators to upload shop list
  - [ ] Add admin page (password-protected, optional)
- [ ] **Autocomplete search**: Use `streamlit-autocomplete` or similar
- [ ] **Product categories**: Group by type (Food, Retail, Services) with filter buttons
- [ ] **Reviews/ratings**: Let users rate products (⭐ 1–5), persist in DB
- [ ] **"Near me" feature**: Show products within 50m of current position (GPS-based)

**Files to Create**:
- [ ] `utils/db.py` – SQLite wrapper
- [ ] `components/product_search_advanced.py`
- [ ] `admin/` – admin dashboard (optional early, critical for Phase 3)

---

### 2.3 Multi-Store Support
**Priority**: MEDIUM | **Effort**: 1 week | **Impact**: Scalable to many malls

**Tasks**:
- [ ] **Refactor store definition**: Move `STORES` to `data/stores.json` (currently hardcoded in `utils/gps_verify.py`)
- [ ] **Store selector UI**: Already exists in sidebar – verify it switches between stores correctly
- [ ] **Modular graph loading**: Load graphs from `data/<store_id>/graphs/`
- [ ] **Test with 2–3 different malls**:
  - [ ] Ensure UI gracefully handles different floor counts, graph sizes
  - [ ] Document data structure for new mall onboarding

---

## 🎨 Phase 3: Advanced Features (3–4 weeks) – Next-Level UX

### 3.1 Real-Time Tracking & Live Navigation
**Priority**: MEDIUM | **Effort**: 2 weeks | **Impact**: Turn-by-turn AR-ready

**Tasks**:
- [x] **Persistent GPS tracking** (with user consent): Store location history (MVP file-backed history)
  - [ ] Map current position on floor plan via WiFi trilateration (advanced)
  - [x] Or: Manual "update position" button for simple MVP
- [x] **Live turn-by-turn**: Highlight current step, auto-advance when user reaches waypoint (MVP)
- [x] **Audio directions**: Text-to-speech for turn-by-turn (browser SpeechSynthesis MVP)
- [x] **Off-route detection**: Alert if user deviates from path > 10m
- [x] **Estimated arrival time**: Update dynamically based on walking speed

**Files to Create**:
- [ ] `components/live_navigation.py`
- [ ] `utils/location_tracking.py`

---

### 3.2 Mobile App (React Native / Flutter)
**Priority**: LOW (Phase 4+) | **Effort**: 6+ weeks | **Impact**: On-the-go usability

**Decision**: Only after Streamlit MVP is rock-solid. Consider React Native for code reuse if backend APIs are exposed.

**Approach**:
- [ ] Extract pathfinding logic to a REST API (FastAPI backend)
- [ ] Expose endpoints: `/api/path`, `/api/products/search`, `/api/store/<id>/map`
- [ ] Build React Native frontend consuming these APIs
- [ ] Syncs location history, preferences between web/mobile

---

### 3.3 Analytics & Insights
**Priority**: LOW | **Effort**: 1 week | **Impact**: Data-driven improvements

**Tasks**:
- [x] **Popular routes**: Track which paths users take most (MVP counts stored)
- [x] **Slow areas**: Identify waypoints that slow users down (MVP high-traffic node counts)
- [x] **Search trends**: Which products get searched most? (MVP top search terms)
- [x] **Pathfinding comparison**: Which algorithm is faster in practice? (MVP in-app run summary)

---

## 🛡️ Phase 4: Production Hardening (2–3 weeks) – Reliability & Scale

### 4.1 Testing & QA
**Priority**: HIGH | **Effort**: 2 weeks | **Impact**: Confidence, fewer bug reports

**Tasks**:
- [ ] **Unit tests** (started in Phase 1): Target 75%+ coverage
- [x] **Integration tests**: Test full flow (select start → end → render path → show directions)
- [x] **E2E tests** (Playwright): Automate user journeys in Streamlit (scaffold + smoke tests)
- [x] **Load testing**: How many concurrent users on Streamlit Cloud? (k6 smoke script)
- [ ] **Accessibility audit**: WCAG 2.1 AA compliance (screen reader support, keyboard nav)
  - [ ] Test with NVDA, JAWS
- [ ] **Browser compatibility**: Test Safari, Firefox, Chrome, Edge

---

### 4.2 Security & Data Privacy
**Priority**: HIGH | **Effort**: 1 week | **Impact**: Trust, GDPR compliance

**Tasks**:
- [x] **Sanitize user input**: Product names, search queries (prevent injection)
- [ ] **HTTPS enforcement**: Streamlit Cloud provides this by default ✓
- [x] **GPS data**: Privacy policy + consent modal (GDPR/CCPA)
  - [x] Option to disable GPS permanently (session-level)
  - [x] Don't store GPS history by default
- [x] **API rate limiting**: Session rate limits for search/add/report actions
- [x] **Admin authentication**: Hashed passwords for analytics dashboard

---

### 4.3 Monitoring & Logging
**Priority**: MEDIUM | **Effort**: 3 days | **Impact**: Proactive issue detection

**Tasks**:
- [x] **Error tracking**: Sentry.io (free tier) hook for crash reports
- [x] **Structured logging**: Replace print() → logger (Python logging module)
- [x] **Performance metrics**: Log pathfinding times, graph sizes → identify bottlenecks
- [x] **User feedback widget**: In-app "Report Issue" button
- [x] **Health checks**: Health check runner to verify graphs/products load correctly

---

## 📈 Phase 5: Scaling & Operations (Ongoing)

### 5.1 Deployment & DevOps
**Priority**: MEDIUM | **Effort**: 1 week | **Impact**: Reliable updates

**Tasks**:
- [x] **CI/CD pipeline** (GitHub Actions):
  - [x] Run tests on every PR
  - [x] Auto-deploy to Streamlit Cloud on merge to `main`
- [x] **Environment management**: `.env` file for store configs, API keys
- [x] **Blue-green deployment**: Streamlit Cloud integration + staging branch
- [x] **Rollback plan**: Document how to revert bad releases
- [x] **Database backups**: Daily SQLite backups to S3 (if moving to DB)

---

### 5.2 Operator Tools
**Priority**: MEDIUM | **Effort**: 1 week | **Impact**: Easier maintenance

**Tasks**:
- [x] **Admin dashboard** (Streamlit page):
  - [x] View/edit products, shops, opening hours
  - [x] Upload new floor plans + auto-generate graphs
  - [x] View analytics, error logs
- [x] **Graph editor UI**: Visual tool to add/remove waypoints and edges
  - [x] Click-to-place node editor with edge preview/save (MVP)
- [x] **Documentation generator**: Auto-create README for new malls
- [x] **One-click deploy**: Script to onboard a new mall (copy template, update config)

---

### 5.3 Machine Learning (Future Exploration)
**Priority**: LOW | **Effort**: 4+ weeks | **Impact**: Very high (future)

**Ideas** (post-MVP):
- [ ] **Predict popular routes** based on time of day, day of week → smart recommendations
- [ ] **Crowd-sourced routing**: Real-time user locations → heatmap + congestion avoidance
- [ ] **Personalized routes**: Learn user preferences (avoid stairs, prefer quiet areas)
- [ ] **What's nearby?**: ML-based recommendations ("You're near Nike, also check Adidas")

---

## 🎯 Priority Matrix

| Feature | Priority | Effort | Impact | Phase |
|---------|----------|--------|--------|-------|
| Type hints + unit tests | HIGH | 2d | 🔴 High | 1 |
| UX Polish | HIGH | 3d | 🟡 Medium | 1 |
| Performance optimization | MEDIUM | 2d | 🔴 High | 1 |
| Accessibility mode | HIGH | 5d | 🔴 High | 2 |
| SQLite migration | MEDIUM | 4d | 🟡 Medium | 2 |
| Multi-store support | MEDIUM | 5d | 🟡 Medium | 2 |
| Real-time tracking | MEDIUM | 10d | 🔴 High | 3 |
| Mobile app (React Native) | LOW | 30d | 🔴 High | 4+ |
| Testing & QA | HIGH | 10d | 🔴 High | 4 |
| Security & Privacy | HIGH | 5d | 🔴 High | 4 |
| Monitoring & Logging | MEDIUM | 3d | 🟡 Medium | 4 |
| Admin dashboard | MEDIUM | 5d | 🟡 Medium | 5 |

---

## 📊 Roadmap Timeline

```
Month 1: Phase 1 (Quick Wins)
├─ Week 1-2: Type hints, tests, constants extraction
├─ Week 2: UX polish (keyboard shortcuts, error messages, dark mode)
└─ Week 2: Performance optimization (lazy loading, caching)

Month 2-3: Phase 2 (Feature Enhancement)
├─ Week 3-4: Accessibility + walking time estimation
├─ Week 5: SQLite migration
└─ Week 6: Multi-store support + testing

Month 4-5: Phase 3 (Advanced Features)
├─ Week 7-8: Real-time tracking + live navigation
├─ Week 9: Analytics dashboard
└─ Week 10: Plan mobile app strategy

Month 6-7: Phase 4 (Production Hardening)
├─ Week 11: Comprehensive testing suite
├─ Week 12: Security audit + privacy compliance
└─ Week 13: Monitoring & error tracking

Ongoing: Phase 5 (Scaling)
└─ DevOps, operator tools, ML exploration
```

---

## 🔍 Critical Success Factors

1. **Maintain backwards compatibility** during refactors (versioned API)
2. **User testing**: Get feedback from mall visitors early (Phase 1–2)
3. **Data quality**: Ensure graphs are accurate (test paths with real visitors)
4. **Performance on mobile**: Streamlit can be slow on mobile – consider lite version
5. **Privacy first**: GPS data sensitivity – build trust through transparency

---

## 📚 Resources & References

- **Streamlit docs**: https://docs.streamlit.io
- **A* heuristics**: https://theory.stanford.edu/~amitp/GameProgramming/Heuristics.html
- **WCAG accessibility**: https://www.w3.org/WAI/WCAG21/quickref/
- **SQLite best practices**: https://www.sqlite.org/bestpractice.html
- **Streamlit Cloud deployment**: https://streamlit.io/cloud/docs

---

## 🚀 Next Immediate Actions

**Start with Phase 1 (Week 1-2)**:

1. ✅ Extract constants to `config.py`
2. ✅ Add type hints to `components/`
3. ✅ Write unit tests for algorithms
4. ✅ Add keyboard shortcuts
5. ✅ Improve error messages
6. ✅ Optimize graph caching

**Why Phase 1 first?**
- Low risk, high confidence in delivery
- Builds testing infrastructure (enables faster Phase 2–5)
- Improves developer experience
- No user-facing disruption

---

**Author**: GitHub Copilot  
**For questions, refer to**: `README.md`, `documentation.docx`
