from dotenv import load_dotenv
import os
import httpx

load_dotenv()
lichess_api_token = os.getenv("LICHESS_API_TOKEN")

def get_opening_moves(fen): 

    response = httpx.get("https://explorer.lichess.org/masters",    
                        headers={"Authorization": f"Bearer {lichess_api_token}"},
                        params = {"fen": fen,"topGames": 0,"recentGames": 0, "moves":3})

    response.raise_for_status()
    data = response.json()
    moves = data["moves"]
    resultats = []
    total_position = data["white"] + data["draws"] + data["black"]

    for coup in moves : 
        notation = coup["san"]

        if coup["opening"] is not None:
            name = coup["opening"]["name"]
        else:
            name = None

        total = coup["white"] + coup["draws"] + coup["black"]
        resultat = {
        "uci": coup["uci"],
        "san": notation,
        "opening": name,
        "games_count": total,
        "frequency": total / total_position if total_position > 0 else 0
        }
        resultats.append(resultat)

    return resultats