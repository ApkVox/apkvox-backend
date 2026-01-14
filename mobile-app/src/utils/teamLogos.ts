/**
 * NBA Team Logo Utilities
 * 
 * Maps team names to ESPN CDN logo URLs
 */

// Team name to ESPN abbreviation mapping
const teamAbbreviations: Record<string, string> = {
    // Atlantic Division
    "Boston Celtics": "bos",
    "Brooklyn Nets": "bkn",
    "New York Knicks": "ny",
    "Philadelphia 76ers": "phi",
    "Toronto Raptors": "tor",

    // Central Division
    "Chicago Bulls": "chi",
    "Cleveland Cavaliers": "cle",
    "Detroit Pistons": "det",
    "Indiana Pacers": "ind",
    "Milwaukee Bucks": "mil",

    // Southeast Division
    "Atlanta Hawks": "atl",
    "Charlotte Hornets": "cha",
    "Miami Heat": "mia",
    "Orlando Magic": "orl",
    "Washington Wizards": "wsh",

    // Northwest Division
    "Denver Nuggets": "den",
    "Minnesota Timberwolves": "min",
    "Oklahoma City Thunder": "okc",
    "Portland Trail Blazers": "por",
    "Utah Jazz": "utah",

    // Pacific Division
    "Golden State Warriors": "gs",
    "LA Clippers": "lac",
    "Los Angeles Clippers": "lac",
    "Los Angeles Lakers": "lal",
    "Phoenix Suns": "phx",
    "Sacramento Kings": "sac",

    // Southwest Division
    "Dallas Mavericks": "dal",
    "Houston Rockets": "hou",
    "Memphis Grizzlies": "mem",
    "New Orleans Pelicans": "no",
    "San Antonio Spurs": "sa",
};

// Short team names for display
export const teamShortNames: Record<string, string> = {
    "Boston Celtics": "Celtics",
    "Brooklyn Nets": "Nets",
    "New York Knicks": "Knicks",
    "Philadelphia 76ers": "76ers",
    "Toronto Raptors": "Raptors",
    "Chicago Bulls": "Bulls",
    "Cleveland Cavaliers": "Cavaliers",
    "Detroit Pistons": "Pistons",
    "Indiana Pacers": "Pacers",
    "Milwaukee Bucks": "Bucks",
    "Atlanta Hawks": "Hawks",
    "Charlotte Hornets": "Hornets",
    "Miami Heat": "Heat",
    "Orlando Magic": "Magic",
    "Washington Wizards": "Wizards",
    "Denver Nuggets": "Nuggets",
    "Minnesota Timberwolves": "T-Wolves",
    "Oklahoma City Thunder": "Thunder",
    "Portland Trail Blazers": "Blazers",
    "Utah Jazz": "Jazz",
    "Golden State Warriors": "Warriors",
    "LA Clippers": "Clippers",
    "Los Angeles Clippers": "Clippers",
    "Los Angeles Lakers": "Lakers",
    "Phoenix Suns": "Suns",
    "Sacramento Kings": "Kings",
    "Dallas Mavericks": "Mavs",
    "Houston Rockets": "Rockets",
    "Memphis Grizzlies": "Grizzlies",
    "New Orleans Pelicans": "Pelicans",
    "San Antonio Spurs": "Spurs",
};

// Team primary and secondary colors for gradients
export const teamColors: Record<string, [string, string]> = {
    // Atlantic
    "Boston Celtics": ["#007A33", "#BA9653"],
    "Brooklyn Nets": ["#000000", "#FFFFFF"],
    "New York Knicks": ["#006BB6", "#F58426"],
    "Philadelphia 76ers": ["#006BB6", "#ED174C"],
    "Toronto Raptors": ["#CE1141", "#000000"],

    // Central
    "Chicago Bulls": ["#CE1141", "#000000"],
    "Cleveland Cavaliers": ["#860038", "#041E42"],
    "Detroit Pistons": ["#C8102E", "#1D42BA"],
    "Indiana Pacers": ["#002D62", "#FDBB30"],
    "Milwaukee Bucks": ["#00471B", "#EEE1C6"],

    // Southeast
    "Atlanta Hawks": ["#C1D32F", "#26282A"],
    "Charlotte Hornets": ["#1D1160", "#00788C"],
    "Miami Heat": ["#98002E", "#F9A01B"],
    "Orlando Magic": ["#0077C0", "#C4CED4"],
    "Washington Wizards": ["#002B5C", "#E31837"],

    // Northwest
    "Denver Nuggets": ["#0E2240", "#FEC524"],
    "Minnesota Timberwolves": ["#0C2340", "#236192"],
    "Oklahoma City Thunder": ["#007AC1", "#EF3B24"],
    "Portland Trail Blazers": ["#E03A3E", "#000000"],
    "Utah Jazz": ["#002B5C", "#00471B"],

    // Pacific
    "Golden State Warriors": ["#1D428A", "#FFC72C"],
    "LA Clippers": ["#C8102E", "#1D428A"],
    "Los Angeles Clippers": ["#C8102E", "#1D428A"],
    "Los Angeles Lakers": ["#552583", "#FDB927"],
    "Phoenix Suns": ["#1D1160", "#E56020"],
    "Sacramento Kings": ["#5A2D81", "#63727A"],

    // Southwest
    "Dallas Mavericks": ["#00538C", "#002B5E"],
    "Houston Rockets": ["#CE1141", "#000000"],
    "Memphis Grizzlies": ["#5D76A9", "#12173F"],
    "New Orleans Pelicans": ["#0C2340", "#8590AA"],
    "San Antonio Spurs": ["#000000", "#C6CFD5"],
};

/**
 * Get team colors for gradients
 * @param teamName Full team name
 * @returns Array of [primary, secondary] colors
 */
export function getTeamColors(teamName: string): [string, string] {
    return teamColors[teamName] || ["#000000", "#444444"]; // Default fallback
}

/**
 * Get the ESPN CDN logo URL for a team
 * @param teamName Full team name (e.g., "Los Angeles Lakers")
 * @returns Logo URL string
 */
export function getTeamLogoUrl(teamName: string): string {
    const abbrev = teamAbbreviations[teamName];
    if (abbrev) {
        return `https://a.espncdn.com/i/teamlogos/nba/500/${abbrev}.png`;
    }
    // Fallback - try to create URL from team name
    const fallback = teamName.toLowerCase().split(' ').pop() || 'nba';
    return `https://a.espncdn.com/i/teamlogos/nba/500/${fallback}.png`;
}

/**
 * Get short display name for a team
 * @param teamName Full team name
 * @returns Short name (e.g., "Lakers")
 */
export function getTeamShortName(teamName: string): string {
    return teamShortNames[teamName] || teamName.split(' ').pop() || teamName;
}

/**
 * Get full team name (passthrough or lookup if needed)
 */
export function getTeamFullName(teamName: string): string {
    return teamName;
}

export default {
    getTeamLogoUrl,
    getTeamShortName,
    getTeamFullName,
    teamShortNames,
    teamColors,
};
