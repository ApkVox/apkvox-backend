import sys
import os
from datetime import datetime, date
import pandas as pd

# Add root to sys.path
sys.path.insert(0, os.getcwd())

from backend.predictor import get_prediction_service

def validate_date(target_date_str):
    service = get_prediction_service()
    if not service.load_models():
        print("Failed to load models")
        return

    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    print(f"Generating predictions for {target_date_str}...")
    
    # Get predictions
    # Note: get_upcoming_predictions usually filters for future, so we use _predict_for_date directly
    # But _predict_for_date is internal. 
    # Let's inspect get_upcoming_predictions to see if it allows past dates.
    # It takes a target_date argument!
    
    predictions = service.get_upcoming_predictions(target_date=target_date)
    
    # We need ACTUAL results. Ideally from our dataset or schedule.
    # Let's use the schedule we already have loaded in the service
    schedule_df = service._load_schedule()
    
    # Filter schedule for this date
    # Adjust for NBA day logic (similar to predictor)
    nba_time = schedule_df["Date"] - pd.Timedelta(hours=6)
    actual_games = schedule_df[nba_time.dt.date == target_date.date()]
    
    results = []
    correct_count = 0
    total_games = 0
    
    report_lines = [f"# Validation Report for {target_date_str}", ""]
    report_lines.append("| Matchup | Predicted Winner | Confidence | Recommendation | AI Impact | Actual Winner | Score | Result |")
    report_lines.append("|---|---|---|---|---|---|---|---|")
    
    print(f"Found {len(actual_games)} actual games in schedule.")
    
    print(f"Found {len(actual_games)} actual games in schedule.")
    
    # Debug: Print available predictions
    print("\nPredicted Games:")
    for p in predictions:
        print(f"  {p['away_team']} @ {p['home_team']}")
        
    # FETCH ACTUAL SCORES FROM EXTERNAL SOURCE (NBA API)
    # Because local CSV might not be updated
    import requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.nba.com/",
        "Accept-Language": "en-US,en;q=0.9"
    }
    date_formatted = target_date.strftime("%m/%d/%Y") # NBA API expects MM/DD/YYYY
    # Using scoreboardV2
    url = f"https://stats.nba.com/stats/scoreboardv2?GameDate={date_formatted}&LeagueID=00&DayOffset=0"
    
    print(f"\nFetching authentic scores from NBA API for {date_formatted}...")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        
        # Check if we got data
        if not data['resultSets'][1]['rowSet']:
            # Fallback: Try previous year (Simulated Date handling)
            # If target is 2026, real data might be 2025
            real_year = target_date.year - 1
            real_date = target_date.replace(year=real_year)
            date_formatted_real = real_date.strftime("%m/%d/%Y")
            print(f"No data for {date_formatted}. Trying {date_formatted_real} (assuming year offset)...")
            url = f"https://stats.nba.com/stats/scoreboardv2?GameDate={date_formatted_real}&LeagueID=00&DayOffset=0"
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()

        headers_ls = data['resultSets'][1]['headers']
        rows_ls = data['resultSets'][1]['rowSet']
        df_scores = pd.DataFrame(rows_ls, columns=headers_ls)
        
        headers_gh = data['resultSets'][0]['headers']
        rows_gh = data['resultSets'][0]['rowSet']
        df_gh = pd.DataFrame(rows_gh, columns=headers_gh)
        
        game_map_live = {}
        
        for _, game in df_gh.iterrows():
            gid = game["GAME_ID"]
            hid = game["HOME_TEAM_ID"]
            vid = game["VISITOR_TEAM_ID"]
            
            # Get scores from LineScore
            h_row = df_scores[df_scores["TEAM_ID"] == hid]
            v_row = df_scores[df_scores["TEAM_ID"] == vid]
            
            if h_row.empty or v_row.empty: continue
            
            h_pts = int(h_row.iloc[0]["PTS"])
            v_pts = int(v_row.iloc[0]["PTS"])
            
            h_name = f"{h_row.iloc[0]['TEAM_CITY_NAME']} {h_row.iloc[0]['TEAM_NAME']}"
            v_name = f"{v_row.iloc[0]['TEAM_CITY_NAME']} {v_row.iloc[0]['TEAM_NAME']}"
            
            # Clean up names
            if h_name == "LA Clippers": h_name = "Los Angeles Clippers"
            if v_name == "LA Clippers": v_name = "Los Angeles Clippers"
            
            game_map_live[(h_name, v_name)] = (h_pts, v_pts)
            
        print(f"Fetched {len(game_map_live)} results from API.")
            
    except Exception as e:
        print(f"Failed to fetch from API: {e}")
        game_map_live = {}
    
    print("\nActual Games (Validated):")
    
    for _, row in actual_games.iterrows():
        home = row["Home Team"]
        away = row["Away Team"]
        result = row["Result"]
        
        h_score = None
        a_score = None
        
        # 1. From CSV
        if isinstance(result, str) and " - " in result:
             try:
                parts = result.split(" - ")
                h_score = int(parts[0])
                a_score = int(parts[1])
             except: pass
             
        # 2. From Live API
        if (home, away) in game_map_live:
            h_score, a_score = game_map_live[(home, away)]
            
        if h_score is None or a_score is None:
            print(f"  {away} @ {home} (Score Missing - Pending)")
            actual_winner = "Pending"
            score_out = "N/A"
            is_correct = None
            result_icon = "⏳"
        else:
            print(f"  {away} @ {home} (Final: {a_score}-{h_score})")
            total_games += 1
            actual_winner = home if h_score > a_score else away
            score_out = f"{int(a_score)}-{int(h_score)}"
            
        # Find matching prediction
        pred = next((p for p in predictions if p["home_team"] == home and p["away_team"] == away), None)
        
        if pred:
            predicted_winner = pred["predicted_winner"]
            confidence = pred["winner_confidence"]
            rec = pred.get("recommendation", "N/A")
            edge = pred.get("edge_percent", 0.0)
            
            # Extract AI Data if available
            ai_data = pred.get("ai_impact", {})
            ai_score = ai_data.get("impact_score", 0.0)
            ai_text = f"{ai_score:.1f}"
            if ai_score < -3.0: ai_text = f"📉 {ai_text}"
            elif ai_score > 3.0: ai_text = f"📈 {ai_score:.1f}"
            
            if actual_winner != "Pending":
                is_correct = (predicted_winner == actual_winner)
                result_icon = "✅" if is_correct else "❌"
                if is_correct: correct_count += 1
            
            # Highlight BETs
            rec_icon = "🟢" if "BET" in rec else "⚪"
            
            line = f"| {away} @ {home} | **{predicted_winner}** | {confidence}% | {rec_icon} {rec} (Edge {edge}%) | {ai_text} | {actual_winner} | {score_out} | {result_icon} |"
            report_lines.append(line)
        else:
            report_lines.append(f"| {away} @ {home} | *No Prediction* | - | - | - | {actual_winner} | {score_out} | ❓ |")

    accuracy = (correct_count / total_games * 100) if total_games > 0 else 0
    summary = f"\n**Accuracy: {correct_count}/{total_games} ({accuracy:.1f}%)**"
    report_lines.append(summary)
    
    # Write to file
    with open("validation_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"Report written to validation_report.md")
    print(f"Accuracy: {accuracy:.1f}%")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = "2026-01-14"
        
    validate_date(date_str)
