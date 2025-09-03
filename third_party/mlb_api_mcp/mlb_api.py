from datetime import datetime
from typing import List, Optional
from pathlib import Path

import mlbstatsapi
from pybaseball import statcast, statcast_batter, statcast_pitcher

mlb = mlbstatsapi.Mlb()


def get_multiple_player_stats(
    mlb, person_ids: list, stats: list, groups: list, season: Optional[int] = None, **params
) -> dict:
    """
    returns stat data for a team

    Parameters
    ----------
    mlb : mlbstatsapi.Mlb
        The MLB stats API instance
    person_ids : list
        the person ids
    stats : list
        list of stat types. List of statTypes can be found at https://statsapi.mlb.com/api/v1/statTypes
    groups : list
        list of stat grous. List of statGroups can be found at https://statsapi.mlb.com/api/v1/statGroups
    season : str, optional
        Insert year to return team stats for a particular season, season=2018
    eventType : str, optional
        Notes for individual events for playLog, playlog can be filered by individual events.
        List of eventTypes can be found at https://statsapi.mlb.com/api/v1/eventTypes

    Returns
    -------
    dict
        returns a dict of stats

    See Also
    --------
    Mlb.get_stats : Get stats
    Mlb.get_team_stats : Get team stats
    Mlb.get_players_stats_for_game : Get player stats for a game

    Examples
    --------
    >>> mlb = Mlb()
    >>> stats = ['season', 'seasonAdvanced']
    >>> groups = ['hitting']
    >>> mlb.get_player_stats(647351, stats, groups)
    {'hitting': {'season': [HittingSeason], 'seasonadvanced': [HittingSeasonAdvanced] }}
    """
    from mlbstatsapi import mlb_module

    params["stats"] = stats
    params["group"] = groups

    hydrate_arr = []
    if groups:
        hydrate_arr.append(f"group=[{','.join(groups)}]")
    if stats:
        hydrate_arr.append(f"type=[{','.join(stats)}]")
    if season:
        hydrate_arr.append(f"season={season}")

    mlb_data = mlb._mlb_adapter_v1.get(
        endpoint=f"people?personIds={','.join(person_ids)}&hydrate=stats({','.join(hydrate_arr)})"
    )
    if 400 <= mlb_data.status_code <= 499:
        return {}

    splits = []

    for person in mlb_data.data["people"]:
        if person.get("stats"):
            splits.append(mlb_module.create_split_data(person["stats"]))

    return splits


def get_sabermetrics_for_players(
    mlb, player_ids: list, season: int, stat_name: Optional[str] = None, group: str = "hitting"
) -> dict:
    """
    Get sabermetric statistics (like WAR) for multiple players for a specific season.

    Parameters
    ----------
    mlb : mlbstatsapi.Mlb
        The MLB stats API instance
    player_ids : list
        List of player IDs to get sabermetrics for
    season : int
        The season year to get stats for
    stat_name : str, optional
        Specific sabermetric stat to extract (e.g., 'war', 'woba', 'wRc'). If None, returns all sabermetrics.
    group : str, optional
        The stat group ('hitting' or 'pitching'). Default is 'hitting'.

    Returns
    -------
    dict
        Dictionary containing player sabermetrics data
    """

    # Build the API endpoint URL
    endpoint = f"stats?stats=sabermetrics&group={group}&sportId=1&season={season}"

    # Make the API call directly
    response = mlb._mlb_adapter_v1.get(endpoint=endpoint)

    if 400 <= response.status_code <= 499:
        return {"error": f"API error: {response.status_code}"}

    if not response.data or "stats" not in response.data:
        return {"error": "No stats data found"}

    # Extract the relevant data
    result = {"season": season, "group": group, "players": []}

    # Filter for our specific players
    player_ids_int = [int(pid) for pid in player_ids]

    for stat_group in response.data["stats"]:
        if "splits" in stat_group:
            for split in stat_group["splits"]:
                if "player" in split and split["player"]["id"] in player_ids_int:
                    player_data = {
                        "player_id": split["player"]["id"],
                        "player_name": split["player"].get("fullName", "Unknown"),
                    }
                    if stat_name and isinstance(split.get("stat"), dict):
                        # Return only one sabermetric stat
                        if stat_name in split["stat"]:
                            player_data[stat_name] = split["stat"][stat_name]
                        else:
                            player_data[stat_name] = None
                            player_data["available_stats"] = list(split["stat"].keys())
                    else:
                        # Return all sabermetric stats
                        player_data["sabermetrics"] = split["stat"]

                    result["players"].append(player_data)

    return result


def get_team_id_from_name(team: str) -> Optional[int]:
    """Helper to get team ID from team name, partial name, or stringified ID."""
    # Accept stringified integer as ID
    try:
        return int(team)
    except (ValueError, TypeError):
        pass
    import csv

    team_lower = team.lower().strip()
    csv_path = Path(__file__).resolve().parent / "current_mlb_teams.csv"
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        # First, try exact match
        for row in reader:
            if team_lower == row["team_name"].lower().strip():
                return int(row["team_id"])
        f.seek(0)
        next(reader)  # skip header
        # Then, try substring match
        for row in reader:
            if team_lower in row["team_name"].lower():
                return int(row["team_id"])
    return None


def get_team_abbreviation_from_name(team: str) -> Optional[str]:
    """
    Given a team name, partial name, or ID, return the 3-letter team abbreviation (e.g., 'NYY' for Yankees).
    Returns None if not found.
    """
    team_id = get_team_id_from_name(team)
    if team_id is None:
        return None
    team_info = mlb.get_team(team_id)
    return getattr(team_info, "abbreviation", None)


def check_result_size(result: dict, context: str) -> Optional[dict]:
    """
    Utility to check the size of a result dictionary (by word count). Returns an error dict if too large, else None.
    """
    import json

    word_count = len(json.dumps(result).split())
    if word_count > 100000:
        return {
            "error": (
                f"Result too large ({word_count} words). Please narrow your query "
                f"(e.g., shorter date range, specific {context})."
            )
        }
    return None


def validate_date_range(start_date: str, end_date: str) -> Optional[dict]:
    """
    Utility to check that start_date is before or equal to end_date.
    Returns an error dict if invalid, else None.
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if start > end:
            return {"error": f"start_date ({start_date}) must be before or equal to end_date ({end_date})"}
    except Exception as e:
        return {"error": f"Invalid date format: {e}"}
    return None


def setup_mlb_tools(mcp):
    """
    Setup MLB tools for the MCP server
    """

    @mcp.tool()
    def get_mlb_standings(season: Optional[int] = None, league: Optional[str] = None) -> dict:
        """
        Get MLB standings for the specified season and league.

        Args:
            season (Optional[int]): The season year. If None, uses current year.
            league (Optional[str]): Filter by league ('AL' or 'NL').

        Returns:
            dict: MLB standings data.
        """
        try:
            if season is None:
                season = datetime.now().year
            params = {}
            if league:
                league = league.upper()
                if league not in ["AL", "NL"]:
                    return {"error": "Invalid league. Use 'AL' or 'NL'."}
                params["league"] = league

            standings = mlb.get_standings(season=season, **params)
            return {"season": season, "standings": standings}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_schedule(
        start_date: str,
        end_date: str,
        team: Optional[str] = None,
    ) -> dict:
        """
        Get MLB schedule between start_date and end_date, optionally filtered by team.

        Args:
            start_date (str): The start date in 'YYYY-MM-DD' format.
            end_date (str): The end date in 'YYYY-MM-DD' format.
            team (Optional[str]): Team ID or team name.

        Returns:
            dict: MLB schedule data.
        """
        try:
            # Validate date range
            date_error = validate_date_range(start_date, end_date)
            if date_error:
                return date_error
            params = {}
            if team is not None:
                team_id = get_team_id_from_name(team)
                if team_id is None:
                    return {"error": f"Team not found: {team}"}
                params["team_id"] = team_id
            schedule = mlb.get_schedule(start_date=start_date, end_date=end_date, **params)
            if not schedule:
                return {"error": "No games found for the given date range"}
            return {"schedule": schedule}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_team_info(team: str) -> dict:
        """
        Get detailed information for a specific team by name or ID.

        Args:
            team (str): Team ID or team name.

        Returns:
            dict: Team information.
        """
        try:
            team_id = get_team_id_from_name(team)
            if team_id is None:
                return {"error": f"Team not found: {team}"}
            team_info = mlb.get_team(team_id)
            return {"team_info": team_info}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_player_info(player_id: int) -> dict:
        """
        Get detailed information for a specific player by ID.

        Args:
            player_id (int): The player ID.

        Returns:
            dict: Player information.
        """
        try:
            player_info = mlb.get_person(player_id)
            return {"player_info": player_info}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_boxscore(game_id: int) -> dict:
        """
        Get box score information for a specific game by game_id.

        Args:
            game_id (int): The game ID.

        Returns:
            dict: Boxscore information.
        """
        try:
            boxscore = mlb.get_game_box_score(game_id)
            return {"boxscore": boxscore}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_multiple_mlb_player_stats(player_ids: str, group: str, type: str, season: Optional[int] = None) -> dict:
        """
        Get stats for multiple players.

        Args:
            player_ids (str): Comma-separated string of player IDs.
            group (str): The stat group (e.g., 'hitting', 'pitching').
            type (str): The stat type (e.g., 'season', 'seasonAdvanced').
            season (Optional[int]): The season year.

        Returns:
            dict: Player stats.
        """
        try:
            person_ids = [pid.strip() for pid in player_ids.split(",") if pid.strip()]
            if not person_ids:
                return {"error": "No player IDs provided"}
            stats = [type]
            groups = [group]
            result = get_multiple_player_stats(mlb, person_ids, stats, groups, season)
            return {"player_stats": result}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_sabermetrics(player_ids: str, season: int, group: str = "hitting", stat_name: Optional[str] = None) -> dict:
        """
        Get sabermetric statistics (like WAR) for multiple players.

        Args:
            player_ids (str): Comma-separated string of player IDs.
            season (int): The season year.
            group (str, optional): Stat group ('hitting' or 'pitching'). Defaults to 'hitting'.
            stat_name (Optional[str], optional): Specific sabermetric stat to extract.

        Returns:
            dict: Player sabermetric statistics.
        """
        try:
            player_ids_list = [pid.strip() for pid in player_ids.split(",") if pid.strip()]
            if not player_ids_list:
                return {"error": "No player IDs provided"}
            result = get_sabermetrics_for_players(mlb, player_ids_list, season, stat_name, group)
            return result
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_game_highlights(game_id: int) -> dict:
        """
        Get highlights content for a specific game.

        Args:
            game_id (int): The game ID.

        Returns:
            dict: Game highlights content.
        """
        try:
            game = mlb.get_game(game_id)
            highlights = getattr(getattr(game, "content", {}), "highlights", {})
            return {"highlights": highlights}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_game_pace(season: Optional[int] = None) -> dict:
        """
        Get game pace information.

        Args:
            season (Optional[int]): Season year.

        Returns:
            dict: Game pace data.
        """
        try:
            params = {}
            if season:
                params["season"] = season
            pace = mlb.get_gamepace(**params)
            return {"pace": pace}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_game_scoring_plays(game_id: int, eventType: str = "scoring_play") -> dict:
        """
        Get scoring plays from a game's play-by-play data.

        Args:
            game_id (int): The game ID.
            eventType (str, optional): The type of event to filter. Default is 'scoring_play'.

        Returns:
            dict: Scoring plays from the game.
        """
        try:
            plays = mlb.get_game_play_by_play(game_id)
            scoring_plays = []
            if hasattr(plays, "allplays") and plays.allplays:
                for play in plays.allplays:
                    if getattr(getattr(play, "result", {}), "eventType", None) == eventType:
                        scoring_plays.append(play)
            return {"plays": scoring_plays}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_linescore(game_id: int) -> dict:
        """
        Get the line score for a specific game.

        Args:
            game_id (int): The game ID.

        Returns:
            dict: The game's line score.
        """
        try:
            linescore = mlb.get_game_line_score(game_id)
            return {"linescore": linescore}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_roster(team: str, date: Optional[str] = None, rosterType: Optional[str] = None) -> dict:
        """
        Get the roster for a specific team, optionally at a specific date and roster type.

        Args:
            team (str): Team ID or team name.
            date (Optional[str], optional): Date for historical roster in 'YYYY-MM-DD' format.
            rosterType (Optional[str], optional): Roster type (e.g., '40Man', 'fullSeason').

        Returns:
            dict: Team roster information.
        """
        try:
            team_id = get_team_id_from_name(team)
            if team_id is None:
                return {"error": f"Team not found: {team}"}
            params = {"team_id": team_id}
            if date:
                params["date"] = date
            if rosterType:
                params["rosterType"] = rosterType
            roster = mlb.get_team_roster(**params)
            return {"roster": roster}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_search_players(fullname: str) -> dict:
        """
        Search for players by full name and return their IDs.

        Args:
            fullname (str): The player's full name.

        Returns:
            dict: Search results including player IDs.
        """
        try:
            player_ids = mlb.get_people_id(fullname)
            return {"player_ids": player_ids}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_players(sport_id: int = 1) -> dict:
        """
        Get all players for a specific sport.

        Args:
            sport_id (int): Sport ID (default: 1 for MLB).

        Returns:
            dict: All players for the specified sport.
        """
        try:
            players = mlb.get_people(sport_id=sport_id)
            return {"players": players}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_draft(year_id: int) -> dict:
        """
        Get MLB draft information for a specific year.

        Args:
            year_id (int): The year of the draft.

        Returns:
            dict: MLB draft information.
        """
        try:
            draft = mlb.get_draft(year_id=year_id)
            return {"draft": draft}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_awards(award_id: int) -> dict:
        """
        Get MLB awards information by award ID.

        Args:
            award_id (int): The award ID.

        Returns:
            dict: MLB awards information.
        """
        try:
            awards = mlb.get_awards(award_id)
            return {"awards": awards}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_search_teams(team_name: str, search_key: str = "all") -> dict:
        """
        Search for MLB teams by full or partial name, return team_id and team_name.

        Args:
            team_name (str): Full or partial team name, or team ID as string.
            search_key (str, optional): One of 'id', 'name', or 'all' (default 'all').

        Returns:
            dict: Matching team records with 'team_id' and 'team_name'.
        """
        try:
            import csv

            teams = []
            csv_path = Path(__file__).resolve().parent / "current_mlb_teams.csv"
            with open(csv_path, "r") as f:
                reader = csv.DictReader(f)
                # Read all rows from CSV
                for row in reader:
                    teams.append(row)

            # Search for teams
            results = []
            for team in teams:
                if search_key == "id":
                    if team_name == team["team_id"]:
                        results.append(team)
                elif search_key == "name":
                    if team_name.lower() in team["team_name"].lower():
                        results.append(team)
                else:  # search_key == "all"
                    if team_name == team["team_id"] or team_name.lower() in team["team_name"].lower():
                        results.append(team)

            return {"teams": results}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_teams(sport_id: int = 1, season: Optional[int] = None) -> dict:
        """
        Get all teams for a specific sport.

        Args:
            sport_id (int): Sport ID (default: 1 for MLB).
            season (Optional[int]): Filter teams by a specific season (year).

        Returns:
            dict: All teams for the specified sport.
        """
        try:
            params = {}
            if season is not None:
                params["season"] = season
            teams = mlb.get_teams(sport_id=sport_id, **params)
            return {"teams": teams}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_mlb_game_lineup(game_id: int) -> dict:
        """
        Get lineup information for a specific game by game_id.

        Args:
            game_id (int): The game ID.

        Returns:
            dict: Game lineup information.
        """
        try:
            # Get the boxscore data
            boxscore = mlb.get_game_box_score(game_id)

            result = {"game_id": game_id, "teams": {}}

            # Process both teams (away and home)
            for team_type in ["away", "home"]:
                if hasattr(boxscore, "teams") and hasattr(boxscore.teams, team_type):
                    team_data = getattr(boxscore.teams, team_type)

                    team_info = {
                        "team_name": getattr(team_data.team, "name", "Unknown"),
                        "team_id": getattr(team_data.team, "id", None),
                        "players": [],
                    }

                    # Get players from the team data
                    if hasattr(team_data, "players") and team_data.players is not None:
                        players_dict = team_data.players

                        # Extract player information
                        for player_key, player_data in players_dict.items():
                            if player_key.startswith("id"):
                                player_info = {
                                    "player_id": getattr(player_data.person, "id", None),
                                    "player_name": getattr(player_data.person, "fullname", "Unknown"),
                                    "jersey_number": getattr(player_data, "jerseynumber", None),
                                    "positions": [],
                                    "batting_order": None,
                                    "game_entries": [],
                                }

                                # Get position information
                                if hasattr(player_data, "allpositions") and player_data.allpositions is not None:
                                    for position in player_data.allpositions:
                                        position_info = {
                                            "position": getattr(position, "abbreviation", None),
                                            "position_name": getattr(position, "name", None),
                                        }
                                        player_info["positions"].append(position_info)

                                # Get batting order from player data directly
                                if hasattr(player_data, "battingorder"):
                                    player_info["batting_order"] = getattr(player_data, "battingorder", None)

                                # Get game entry information (substitutions, etc.)
                                if hasattr(player_data, "gamestatus"):
                                    game_status = player_data.gamestatus
                                    entry_info = {
                                        "is_on_bench": getattr(game_status, "isonbench", False),
                                        "is_substitute": getattr(game_status, "issubstitute", False),
                                        "status": getattr(game_status, "status", None),
                                    }
                                    player_info["game_entries"].append(entry_info)

                                team_info["players"].append(player_info)

                    # Sort players by batting order (starting lineup first, then substitutes)
                    def sort_key(player):
                        batting_order = player.get("batting_order")
                        if batting_order is None:
                            return 999  # Put non-batting order players at the end
                        return int(str(batting_order).replace("0", ""))  # Handle batting order formatting

                    team_info["players"].sort(key=sort_key)
                    result["teams"][team_type] = team_info

            return result
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_statcast_pitcher(
        player_id: int,
        start_date: str,
        end_date: str,
    ) -> dict:
        """
        Retrieve MLB Statcast data for a pitcher over a date range.

        Parameters
        ----------
        player_id : int
            The player ID for the pitcher.
        start_date : str
            The start date in 'YYYY-MM-DD' format. Required.
        end_date : str
            The end date in 'YYYY-MM-DD' format. Required.

        Returns
        -------
        dict
            Dictionary with Statcast data for the pitcher. If the result is too large, returns an error message.

        Notes
        -----
        Data is sourced from MLB Statcast via pybaseball. See the official documentation for more details:
        https://github.com/jldbc/pybaseball/tree/master/docs
        """
        try:
            # Validate date range
            date_error = validate_date_range(start_date, end_date)
            if date_error:
                return date_error
            data = statcast_pitcher(start_date, end_date, player_id)
            # Convert all columns to string to ensure JSON serializability
            data = data.astype(str)
            result = {"statcast_data": data.to_dict(orient="records")}
            if not result["statcast_data"]:
                return {
                    "error": (
                        f"No Statcast data found for the given date range ({start_date} to {end_date}). The date "
                        "range may have resulted in nothing being returned."
                    )
                }
            size_error = check_result_size(result, "player")
            if size_error:
                return size_error
            return result
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_statcast_batter(
        player_id: int,
        start_date: str,
        end_date: str,
    ) -> dict:
        """
        Retrieve MLB Statcast data for a batter over a date range.

        Parameters
        ----------
        player_id : int
            The player ID for the batter.
        start_date : str
            The start date in 'YYYY-MM-DD' format. Required.
        end_date : str
            The end date in 'YYYY-MM-DD' format. Required.

        Returns
        -------
        dict
            Dictionary with Statcast data for the batter. If the result is too large, returns an error message.

        Notes
        -----
        Data is sourced from MLB Statcast via pybaseball. See the official documentation for more details:
        https://github.com/jldbc/pybaseball/tree/master/docs
        """
        try:
            # Validate date range
            date_error = validate_date_range(start_date, end_date)
            if date_error:
                return date_error
            data = statcast_batter(start_date, end_date, player_id)
            # Convert all columns to string to ensure JSON serializability
            data = data.astype(str)
            result = {"statcast_data": data.to_dict(orient="records")}
            if not result["statcast_data"]:
                return {
                    "error": (
                        f"No Statcast data found for the given date range ({start_date} to {end_date}). The date "
                        "range may have resulted in nothing being returned."
                    )
                }
            size_error = check_result_size(result, "player")
            if size_error:
                return size_error
            return result
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_statcast_team(
        team: str,
        start_date: str,
        end_date: str,
        fields: List[str],
    ) -> dict:
        """
        Retrieve MLB Statcast data for all players on a team over a date range.

        Parameters
        ----------
        team : str
            Team ID or team name (see MLB team list for valid values).
        start_date : str
            The start date in 'YYYY-MM-DD' format. Required.
        end_date : str
            The end date in 'YYYY-MM-DD' format. Required.
        fields: List[str]
            The field to return. If not provided, defaults to all fields. Available fields:
                 pitch_type, game_date, release_speed, release_pos_x, release_pos_z, player_name, batter, pitcher,
                 events, description, spin_dir, spin_rate_deprecated, break_angle_deprecated, break_length_deprecated,
                 zone, des, game_type, stand, p_throws, home_team, away_team, type, hit_location, bb_type, balls,
                 strikes, game_year, pfx_x, pfx_z, plate_x, plate_z, on_3b, on_2b, on_1b, outs_when_up, inning,
                 inning_topbot, hc_x, hc_y, tfs_deprecated, tfs_zulu_deprecated, umpire, sv_id, vx0, vy0, vz0, ax, ay,
                 az, sz_top, sz_bot, hit_distance_sc, launch_speed, launch_angle, effective_speed, release_spin_rate,
                 release_extension, game_pk, fielder_2, fielder_3, fielder_4, fielder_5, fielder_6, fielder_7,
                 fielder_8, fielder_9, release_pos_y, estimated_ba_using_speedangle,
                 estimated_woba_using_speedangle, woba_value, woba_denom, babip_value, iso_value, launch_speed_angle,
                 at_bat_number, pitch_number, pitch_name, home_score, away_score, bat_score, fld_score,
                 post_away_score, post_home_score, post_bat_score, post_fld_score, if_fielding_alignment,
                 of_fielding_alignment, spin_axis, delta_home_win_exp, delta_run_exp, bat_speed, swing_length,
                 estimated_slg_using_speedangle, delta_pitcher_run_exp, hyper_speed, home_score_diff, bat_score_diff,
                 home_win_exp, bat_win_exp, age_pit_legacy, age_bat_legacy, age_pit, age_bat, n_thruorder_pitcher,
                 n_priorpa_thisgame_player_at_bat, pitcher_days_since_prev_game, batter_days_since_prev_game,
                 pitcher_days_until_next_game, batter_days_until_next_game, api_break_z_with_gravity,
                 api_break_x_arm, api_break_x_batter_in, arm_angle, attack_angle, attack_direction, swing_path_tilt,
                 intercept_ball_minus_batter_pos_x_inches, intercept_ball_minus_batter_pos_y_inches
        Returns
        -------
        dict
            Dictionary with Statcast data for all players on the team. If the result is too large, returns an error
            message.
        Notes
        -----
        This uses the pybaseball `statcast` function, which returns all Statcast events for the specified team and date
        range. See the official documentation for more details:
        https://github.com/jldbc/pybaseball/tree/master/docs
        """
        try:
            # Validate date range
            date_error = validate_date_range(start_date, end_date)
            if date_error:
                return date_error
            abbreviation = get_team_abbreviation_from_name(team)
            if not abbreviation:
                return {"error": f"Could not find 3-letter abbreviation for team '{team}'"}
            data = statcast(start_date, end_date, team=abbreviation)
            # Convert all columns to string to ensure JSON serializability
            data = data.astype(str)
            records = data.to_dict(orient="records")
            # Always include batter and pitcher, plus all requested fields
            filtered_records = []
            for row in records:
                filtered_row = {}
                for key in ["batter", "pitcher", *list(fields)]:
                    if key in row:
                        filtered_row[key] = row[key]
                filtered_records.append(filtered_row)
            result = {"statcast_data": filtered_records}
            if not result["statcast_data"]:
                return {
                    "error": (
                        f"No Statcast data found for the given date range ({start_date} to {end_date}). The date "
                        "range may have resulted in nothing being returned."
                    )
                }
            size_error = check_result_size(result, "team")
            if size_error:
                return size_error
            return result
        except Exception as e:
            return {"error": str(e)}

