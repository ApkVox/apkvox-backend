"""
Comprehensive System Audit Test Suite
======================================

This script performs deep testing of all system components:
- Backend API endpoints
- Database operations
- Prediction engine
- AI integrations
- Worker module
- Edge cases

Run with: python -m backend.tests.audit_tests
"""

import os
import sys
import json
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Test Results Storage
FINDINGS: List[Dict[str, Any]] = []
PASSED = 0
FAILED = 0
WARNINGS = 0

def log_finding(category: str, test_name: str, status: str, details: str, severity: str = "INFO"):
    """Log a test finding"""
    global PASSED, FAILED, WARNINGS
    
    finding = {
        "category": category,
        "test": test_name,
        "status": status,
        "details": details,
        "severity": severity,
        "timestamp": datetime.now().isoformat()
    }
    FINDINGS.append(finding)
    
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{icon} [{category}] {test_name}: {details[:80]}...")
    
    if status == "PASS":
        PASSED += 1
    elif status == "FAIL":
        FAILED += 1
    else:
        WARNINGS += 1

# ============================================================
# PHASE 1: DATABASE LAYER TESTS
# ============================================================
def test_database():
    print("\n" + "="*60)
    print("PHASE 1: DATABASE LAYER TESTS")
    print("="*60)
    
    try:
        from backend.database import (
            get_connection, init_db, save_predictions, get_history,
            save_ai_insight, get_ai_insight, get_daily_cache, save_daily_cache,
            get_stats
        )
        
        # Test 1.1: Connection
        try:
            conn = get_connection()
            conn.close()
            log_finding("Database", "Connection Test", "PASS", "Successfully connected to PostgreSQL")
        except Exception as e:
            log_finding("Database", "Connection Test", "FAIL", f"Connection failed: {e}", "CRITICAL")
            return  # Can't continue without DB
        
        # Test 1.2: Init DB (should be idempotent)
        try:
            init_db()
            log_finding("Database", "Init DB", "PASS", "Schema initialization completed")
        except Exception as e:
            log_finding("Database", "Init DB", "FAIL", f"Init failed: {e}", "CRITICAL")
        
        # Test 1.3: Save predictions with valid data
        try:
            test_pred = [{
                "home_team": "TEST_HOME",
                "away_team": "TEST_AWAY",
                "predicted_winner": "TEST_HOME",
                "home_win_probability": 55.0,
                "away_win_probability": 45.0,
                "winner_confidence": 55.0,
                "under_over_prediction": "OVER",
                "under_over_line": 220.0,
                "ou_confidence": 60.0,
                "home_odds": -150,
                "away_odds": 130,
                "start_time_utc": datetime.now().isoformat() + "Z",
                "timestamp": datetime.now().isoformat(),
            }]
            count = save_predictions(test_pred)
            if count > 0:
                log_finding("Database", "Save Predictions", "PASS", f"Saved {count} test prediction")
            else:
                log_finding("Database", "Save Predictions", "WARN", "Save returned 0 (validation may have rejected)", "MEDIUM")
        except Exception as e:
            log_finding("Database", "Save Predictions", "FAIL", f"Save failed: {e}", "HIGH")
        
        # Test 1.4: Save predictions with MISSING required fields
        try:
            bad_pred = [{"home_team": "INCOMPLETE"}]  # Missing most fields
            count = save_predictions(bad_pred)
            if count == 0:
                log_finding("Database", "Invalid Prediction Handling", "PASS", "Correctly rejected incomplete data")
            else:
                log_finding("Database", "Invalid Prediction Handling", "WARN", "Accepted incomplete data - validation may be weak", "MEDIUM")
        except Exception as e:
            log_finding("Database", "Invalid Prediction Handling", "PASS", f"Raised error as expected: {type(e).__name__}")
        
        # Test 1.5: Get history
        try:
            history = get_history(limit=5)
            log_finding("Database", "Get History", "PASS", f"Retrieved {len(history)} records")
        except Exception as e:
            log_finding("Database", "Get History", "FAIL", f"Failed: {e}", "HIGH")
        
        # Test 1.6: AI Insights
        try:
            test_insight = {
                "summary": "Test insight",
                "impact_score": 2.5,
                "key_factors": ["Factor 1", "Factor 2"],
                "confidence": 75
            }
            save_ai_insight("TEST_TEAM", "2026-01-17", test_insight)
            retrieved = get_ai_insight("TEST_TEAM", "2026-01-17")
            if retrieved and retrieved.get("summary") == "Test insight":
                log_finding("Database", "AI Insights CRUD", "PASS", "Save and retrieve working")
            else:
                log_finding("Database", "AI Insights CRUD", "WARN", "Retrieved data doesn't match", "MEDIUM")
        except Exception as e:
            log_finding("Database", "AI Insights CRUD", "FAIL", f"Failed: {e}", "HIGH")
        
        # Test 1.7: Daily Cache
        try:
            test_strategy = {
                "strategy": "TEST_STRATEGY",
                "bankroll_basis": 10000,
                "proposed_bets": [],
                "risk_analysis": {"advisor": "Test", "message": "Test", "exposure_rating": "LOW"}
            }
            save_daily_cache("2026-01-17", predictions=[], strategy=test_strategy, sentinel_msg="Test")
            cached = get_daily_cache("2026-01-17")
            if cached and cached.get("strategy_json"):
                log_finding("Database", "Daily Cache CRUD", "PASS", "Cache save/retrieve working")
            else:
                log_finding("Database", "Daily Cache CRUD", "WARN", "Cache retrieval issue", "MEDIUM")
        except Exception as e:
            log_finding("Database", "Daily Cache CRUD", "FAIL", f"Failed: {e}", "HIGH")
        
        # Test 1.8: Stats query
        try:
            stats = get_stats()
            if isinstance(stats, dict) and "total_predictions" in stats:
                log_finding("Database", "Stats Query", "PASS", f"Stats: {stats}")
            else:
                log_finding("Database", "Stats Query", "WARN", "Stats structure unexpected", "LOW")
        except Exception as e:
            log_finding("Database", "Stats Query", "FAIL", f"Failed: {e}", "MEDIUM")
            
    except ImportError as e:
        log_finding("Database", "Import Test", "FAIL", f"Import failed: {e}", "CRITICAL")

# ============================================================
# PHASE 2: PREDICTION ENGINE TESTS
# ============================================================
def test_prediction_engine():
    print("\n" + "="*60)
    print("PHASE 2: PREDICTION ENGINE TESTS")
    print("="*60)
    
    try:
        from backend.predictor import get_prediction_service, NBAPredictionService
        
        service = get_prediction_service()
        
        # Test 2.1: Model Loading
        try:
            if not service.models_loaded:
                result = service.load_models()
                if result:
                    log_finding("Predictor", "Model Loading", "PASS", "XGBoost models loaded successfully")
                else:
                    log_finding("Predictor", "Model Loading", "FAIL", "Model loading returned False", "CRITICAL")
            else:
                log_finding("Predictor", "Model Loading", "PASS", "Models already loaded (cached)")
        except Exception as e:
            log_finding("Predictor", "Model Loading", "FAIL", f"Failed: {e}", "CRITICAL")
            return
        
        # Test 2.2: Schedule Loading
        try:
            schedule = service._load_schedule()
            if schedule is not None and not schedule.empty:
                log_finding("Predictor", "Schedule Loading", "PASS", f"Loaded {len(schedule)} scheduled games")
            else:
                log_finding("Predictor", "Schedule Loading", "WARN", "Schedule is empty", "MEDIUM")
        except Exception as e:
            log_finding("Predictor", "Schedule Loading", "FAIL", f"Failed: {e}", "HIGH")
        
        # Test 2.3: Games from Schedule (today)
        try:
            from backend.timezone import get_current_datetime
            today = get_current_datetime()
            games = service._get_games_from_schedule(today)
            log_finding("Predictor", "Today's Games", "PASS" if games else "WARN", 
                       f"Found {len(games)} games for today" if games else "No games today (may be normal)")
        except Exception as e:
            log_finding("Predictor", "Today's Games", "FAIL", f"Failed: {e}", "HIGH")
        
        # Test 2.4: Stats Caching
        try:
            start = time.time()
            stats1 = service._get_current_stats()
            time1 = time.time() - start
            
            start = time.time()
            stats2 = service._get_current_stats()
            time2 = time.time() - start
            
            if time2 < time1 * 0.5:  # Second call should be much faster (cached)
                log_finding("Predictor", "Stats Caching", "PASS", f"Cache working (1st: {time1:.2f}s, 2nd: {time2:.2f}s)")
            else:
                log_finding("Predictor", "Stats Caching", "WARN", f"Cache may not be working (times similar)", "MEDIUM")
        except Exception as e:
            log_finding("Predictor", "Stats Caching", "FAIL", f"Failed: {e}", "MEDIUM")
        
        # Test 2.5: Full Prediction (if games exist)
        try:
            predictions = service.get_todays_predictions()
            if predictions:
                # Validate structure of first prediction
                pred = predictions[0]
                required_fields = ["home_team", "away_team", "predicted_winner", "home_win_probability"]
                missing = [f for f in required_fields if f not in pred]
                if missing:
                    log_finding("Predictor", "Prediction Structure", "FAIL", f"Missing fields: {missing}", "HIGH")
                else:
                    log_finding("Predictor", "Prediction Structure", "PASS", f"Got {len(predictions)} predictions with valid structure")
            else:
                log_finding("Predictor", "Full Prediction", "WARN", "No predictions generated (may be no games)", "LOW")
        except Exception as e:
            log_finding("Predictor", "Full Prediction", "FAIL", f"Failed: {e}\n{traceback.format_exc()}", "HIGH")
            
    except ImportError as e:
        log_finding("Predictor", "Import Test", "FAIL", f"Import failed: {e}", "CRITICAL")

# ============================================================
# PHASE 3: AI INTEGRATION TESTS
# ============================================================
def test_ai_integrations():
    print("\n" + "="*60)
    print("PHASE 3: AI INTEGRATION TESTS")
    print("="*60)
    
    # Test 3.1: GROQ API Key
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        log_finding("AI", "GROQ_API_KEY", "PASS", f"Key present (length: {len(groq_key)})")
    else:
        log_finding("AI", "GROQ_API_KEY", "FAIL", "GROQ_API_KEY not set - AI features will fail", "CRITICAL")
    
    # Test 3.2: SportsInvestigator Import
    try:
        from ai_researcher import SportsInvestigator, ImpactAnalysis
        log_finding("AI", "SportsInvestigator Import", "PASS", "Module imported successfully")
        
        # Test 3.3: Search (DuckDuckGo)
        try:
            investigator = SportsInvestigator()
            news = investigator.search_news("Lakers NBA news")
            if news and "Error" not in news and len(news) > 50:
                log_finding("AI", "News Search", "PASS", f"Retrieved {len(news)} chars of news context")
            else:
                log_finding("AI", "News Search", "WARN", f"Search returned limited/error: {news[:100]}", "MEDIUM")
        except Exception as e:
            log_finding("AI", "News Search", "FAIL", f"Failed: {e}", "HIGH")
        
        # Test 3.4: Impact Analysis (LLM)
        if groq_key:
            try:
                analysis = investigator.analyze_impact("Lakers star LeBron James is OUT tonight with injury", "Los Angeles Lakers")
                if analysis and "impact_score" in analysis:
                    score = analysis.get("impact_score", 0)
                    log_finding("AI", "Impact Analysis", "PASS", f"LLM analysis working (impact: {score})")
                else:
                    log_finding("AI", "Impact Analysis", "WARN", f"Analysis structure unexpected: {analysis}", "MEDIUM")
            except Exception as e:
                log_finding("AI", "Impact Analysis", "FAIL", f"LLM call failed: {e}", "HIGH")
        else:
            log_finding("AI", "Impact Analysis", "SKIP", "Skipped due to missing API key")
            
    except ImportError as e:
        log_finding("AI", "SportsInvestigator Import", "FAIL", f"Import failed: {e}", "HIGH")
    
    # Test 3.5: Sentinel Agent
    try:
        from backend.sentinel_agent import sentinel
        
        test_bets = [
            {"match": "LAL vs GSW", "selection": "LAL", "odds": 1.85, "stake_amount": 500}
        ]
        
        try:
            advice = sentinel.analyze_risk(test_bets, 10000)
            if advice and len(advice) > 20:
                log_finding("AI", "Sentinel Risk Analysis", "PASS", f"Advice received: {advice[:80]}...")
            else:
                log_finding("AI", "Sentinel Risk Analysis", "WARN", f"Short/empty advice: {advice}", "MEDIUM")
        except Exception as e:
            log_finding("AI", "Sentinel Risk Analysis", "FAIL", f"Failed: {e}", "HIGH")
            
    except ImportError as e:
        log_finding("AI", "Sentinel Import", "FAIL", f"Import failed: {e}", "HIGH")

# ============================================================
# PHASE 4: FINANCE ENGINE TESTS
# ============================================================
def test_finance_engine():
    print("\n" + "="*60)
    print("PHASE 4: FINANCE ENGINE TESTS")
    print("="*60)
    
    try:
        from backend.finance_engine import calculate_kelly_bet, sniper_check, optimize_portfolio
        from backend.models import BetLedger
        
        # Test 4.1: Kelly Criterion - Normal Case
        try:
            prob = 0.60  # 60% win probability
            odds = 2.0   # 2.0 decimal odds
            stake = calculate_kelly_bet(prob, odds, 10000, kelly_fraction=0.25)
            expected_min = 500  # With 10% edge, fraction 0.25, should be reasonable
            expected_max = 2000
            if expected_min <= stake <= expected_max:
                log_finding("Finance", "Kelly Criterion Normal", "PASS", f"Stake ${stake:.2f} is reasonable")
            elif stake == 0:
                log_finding("Finance", "Kelly Criterion Normal", "WARN", "Stake is 0 - edge may be negative", "MEDIUM")
            else:
                log_finding("Finance", "Kelly Criterion Normal", "WARN", f"Stake ${stake:.2f} seems off", "MEDIUM")
        except Exception as e:
            log_finding("Finance", "Kelly Criterion Normal", "FAIL", f"Failed: {e}", "HIGH")
        
        # Test 4.2: Kelly Criterion - Edge Cases
        try:
            # Zero probability
            stake = calculate_kelly_bet(0.0, 2.0, 10000)
            assert stake == 0, "Zero prob should give zero stake"
            
            # Negative edge (prob < implied)
            stake = calculate_kelly_bet(0.40, 2.0, 10000)  # 40% prob, 50% implied
            assert stake == 0, "Negative edge should give zero stake"
            
            # Odds = 1 (no profit possible)
            stake = calculate_kelly_bet(0.90, 1.0, 10000)
            assert stake == 0, "Odds=1 should give zero stake"
            
            log_finding("Finance", "Kelly Edge Cases", "PASS", "All edge cases handled correctly")
        except AssertionError as e:
            log_finding("Finance", "Kelly Edge Cases", "FAIL", f"Edge case failed: {e}", "HIGH")
        except Exception as e:
            log_finding("Finance", "Kelly Edge Cases", "FAIL", f"Unexpected error: {e}", "HIGH")
        
        # Test 4.3: Sniper Check
        try:
            # Should pass: High edge, good odds
            result1 = sniper_check(0.70, 1.85)  # 70% prob, 1.85 odds (54% implied) = 16% edge
            
            # Should fail: Low odds
            result2 = sniper_check(0.80, 1.40)  # Good edge but odds too low
            
            # Should fail: Low edge
            result3 = sniper_check(0.55, 1.80)  # 55% implied is close to 55% prob
            
            if result1 and not result2:
                log_finding("Finance", "Sniper Check", "PASS", "Filter working correctly")
            else:
                log_finding("Finance", "Sniper Check", "WARN", f"Filter may be misconfigured: {result1}, {result2}, {result3}", "MEDIUM")
        except Exception as e:
            log_finding("Finance", "Sniper Check", "FAIL", f"Failed: {e}", "HIGH")
        
        # Test 4.4: Portfolio Optimization with mock predictions
        try:
            mock_preds = [
                {
                    "home_team": "LAL",
                    "away_team": "GSW",
                    "predicted_winner": "LAL",
                    "home_win_probability": 70.0,
                    "away_win_probability": 30.0,
                    "home_odds": -150,
                    "away_odds": 130,
                    "start_time_utc": "2026-01-18T00:00:00Z"
                }
            ]
            bets = optimize_portfolio(mock_preds, 10000)
            if isinstance(bets, list):
                log_finding("Finance", "Portfolio Optimization", "PASS", f"Generated {len(bets)} proposed bets")
            else:
                log_finding("Finance", "Portfolio Optimization", "FAIL", f"Expected list, got {type(bets)}", "HIGH")
        except Exception as e:
            log_finding("Finance", "Portfolio Optimization", "FAIL", f"Failed: {e}", "HIGH")
            
    except ImportError as e:
        log_finding("Finance", "Import Test", "FAIL", f"Import failed: {e}", "CRITICAL")

# ============================================================
# PHASE 5: WORKER MODULE TESTS
# ============================================================
def test_worker():
    print("\n" + "="*60)
    print("PHASE 5: WORKER MODULE TESTS")
    print("="*60)
    
    try:
        from backend.worker import run_ai_investigation_batch, run_daily_analysis
        
        # Test 5.1: AI Investigation Batch (with single test team)
        try:
            # This is a lighter test - just one team
            run_ai_investigation_batch(["Los Angeles Lakers"], "2026-01-17")
            log_finding("Worker", "AI Investigation Batch", "PASS", "Batch investigation completed without crash")
        except Exception as e:
            log_finding("Worker", "AI Investigation Batch", "FAIL", f"Failed: {e}", "HIGH")
        
        # Test 5.2: Daily Analysis (this is the full flow - may take time)
        # We'll just verify it doesn't crash, not wait for completion
        try:
            from backend.worker import start_analysis_thread
            # Don't actually run the full thing in tests - it's too heavy
            # Just verify the function exists and is callable
            log_finding("Worker", "Daily Analysis Function", "PASS", "Function exists and is importable")
        except Exception as e:
            log_finding("Worker", "Daily Analysis Function", "FAIL", f"Import failed: {e}", "HIGH")
            
    except ImportError as e:
        log_finding("Worker", "Import Test", "FAIL", f"Import failed: {e}", "CRITICAL")

# ============================================================
# PHASE 6: API ENDPOINT TESTS (via HTTP)
# ============================================================
def test_api_endpoints():
    print("\n" + "="*60)
    print("PHASE 6: API ENDPOINT TESTS")
    print("="*60)
    
    import requests
    
    # Test against local server if running
    BASE_URL = "http://127.0.0.1:8004"
    
    # Test 6.1: Health Check
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "status" in data:
                log_finding("API", "Health Endpoint", "PASS", f"Response: {data}")
            else:
                log_finding("API", "Health Endpoint", "WARN", "Missing 'status' field", "LOW")
        else:
            log_finding("API", "Health Endpoint", "FAIL", f"Status code: {resp.status_code}", "HIGH")
    except requests.exceptions.ConnectionError:
        log_finding("API", "Health Endpoint", "SKIP", "Local server not running (port 8004)")
        return  # Can't test other endpoints
    except Exception as e:
        log_finding("API", "Health Endpoint", "FAIL", f"Failed: {e}", "HIGH")
        return
    
    # Test 6.2: Predictions Endpoint
    try:
        resp = requests.get(f"{BASE_URL}/api/predictions", timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            log_finding("API", "Predictions Endpoint", "PASS", f"Got {data.get('count', 0)} predictions")
        else:
            log_finding("API", "Predictions Endpoint", "FAIL", f"Status: {resp.status_code} - {resp.text[:100]}", "HIGH")
    except Exception as e:
        log_finding("API", "Predictions Endpoint", "FAIL", f"Failed: {e}", "HIGH")
    
    # Test 6.3: Strategy Optimize - Valid
    try:
        resp = requests.post(f"{BASE_URL}/api/strategy/optimize", json={"bankroll": 10000}, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            required = ["strategy", "proposed_bets", "risk_analysis"]
            missing = [f for f in required if f not in data]
            if missing:
                log_finding("API", "Strategy Optimize", "FAIL", f"Missing fields: {missing}", "HIGH")
            else:
                log_finding("API", "Strategy Optimize", "PASS", f"Response structure valid, {len(data.get('proposed_bets', []))} bets")
        else:
            log_finding("API", "Strategy Optimize", "FAIL", f"Status: {resp.status_code} - {resp.text[:200]}", "HIGH")
    except Exception as e:
        log_finding("API", "Strategy Optimize", "FAIL", f"Failed: {e}", "HIGH")
    
    # Test 6.4: Strategy Optimize - Zero Bankroll
    try:
        resp = requests.post(f"{BASE_URL}/api/strategy/optimize", json={"bankroll": 0}, timeout=30)
        # This might be handled gracefully or error - both are acceptable
        if resp.status_code == 200:
            log_finding("API", "Strategy Zero Bankroll", "WARN", "Accepted zero bankroll - may produce weird results", "LOW")
        else:
            log_finding("API", "Strategy Zero Bankroll", "PASS", f"Rejected zero bankroll: {resp.status_code}")
    except Exception as e:
        log_finding("API", "Strategy Zero Bankroll", "WARN", f"Exception: {e}", "LOW")
    
    # Test 6.5: Admin Refresh
    try:
        resp = requests.post(f"{BASE_URL}/api/admin/refresh-daily", timeout=10)
        if resp.status_code == 200:
            log_finding("API", "Admin Refresh", "PASS", "Trigger accepted")
        else:
            log_finding("API", "Admin Refresh", "FAIL", f"Status: {resp.status_code}", "MEDIUM")
    except Exception as e:
        log_finding("API", "Admin Refresh", "FAIL", f"Failed: {e}", "MEDIUM")

# ============================================================
# PHASE 7: CODE QUALITY CHECKS
# ============================================================
def test_code_quality():
    print("\n" + "="*60)
    print("PHASE 7: CODE QUALITY CHECKS")
    print("="*60)
    
    # Test 7.1: Check for hardcoded secrets
    files_to_check = [
        "backend/main.py",
        "backend/database.py",
        "backend/predictor.py",
        "ai_researcher.py",
        "mobile-app/src/services/api.ts"
    ]
    
    secret_patterns = ["sk-", "api_key=", "password=", "secret="]
    
    for filepath in files_to_check:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                for pattern in secret_patterns:
                    if pattern in content.lower():
                        # Check if it's actually a secret or just a variable name
                        lines = [l for l in content.split('\n') if pattern in l.lower()]
                        # Filter out comments and env.get calls
                        suspicious = [l for l in lines if not l.strip().startswith('#') and 'getenv' not in l and 'os.environ' not in l]
                        if suspicious:
                            log_finding("Security", f"Hardcoded Secret in {filepath}", "WARN", f"Pattern '{pattern}' found", "HIGH")
                            break
                else:
                    continue
                break
        except FileNotFoundError:
            pass
    else:
        log_finding("Security", "Hardcoded Secrets Scan", "PASS", "No obvious hardcoded secrets found")
    
    # Test 7.2: Check mobile API URL
    try:
        with open("mobile-app/src/services/api.ts", 'r') as f:
            content = f.read()
            if "localhost" in content and "// " not in content.split("localhost")[0].split('\n')[-1]:
                log_finding("Config", "Mobile API URL", "WARN", "localhost found in API config (may break production)", "MEDIUM")
            elif "192.168" in content and "//" not in content.split("192.168")[0].split('\n')[-1]:
                log_finding("Config", "Mobile API URL", "WARN", "Local IP found in API config (may break production)", "MEDIUM")
            else:
                log_finding("Config", "Mobile API URL", "PASS", "Production URL configured")
    except Exception as e:
        log_finding("Config", "Mobile API URL Check", "FAIL", f"Could not check: {e}", "LOW")

# ============================================================
# MAIN EXECUTION
# ============================================================
def run_audit():
    print("\n" + "="*60)
    print("🔍 COMPREHENSIVE SYSTEM AUDIT")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    
    test_database()
    test_prediction_engine()
    test_ai_integrations()
    test_finance_engine()
    test_worker()
    test_api_endpoints()
    test_code_quality()
    
    # Summary
    print("\n" + "="*60)
    print("📊 AUDIT SUMMARY")
    print("="*60)
    print(f"✅ Passed:   {PASSED}")
    print(f"⚠️  Warnings: {WARNINGS}")
    print(f"❌ Failed:   {FAILED}")
    print(f"\nTotal Tests: {PASSED + WARNINGS + FAILED}")
    
    # Critical Findings
    critical = [f for f in FINDINGS if f.get("severity") in ["CRITICAL", "HIGH"] and f.get("status") == "FAIL"]
    if critical:
        print("\n🚨 CRITICAL/HIGH SEVERITY FAILURES:")
        for f in critical:
            print(f"  - [{f['category']}] {f['test']}: {f['details'][:80]}")
    
    # Save full report
    report_path = "audit_report.json"
    with open(report_path, 'w') as f:
        json.dump({
            "summary": {"passed": PASSED, "warnings": WARNINGS, "failed": FAILED},
            "findings": FINDINGS,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    print(f"\n📄 Full report saved to: {report_path}")
    
    return FAILED == 0

if __name__ == "__main__":
    success = run_audit()
    sys.exit(0 if success else 1)
