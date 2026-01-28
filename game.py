import random,math
class Player:
    def __init__(self,letter):
        self.letter=letter
    def get_move(self):
        pass
class HumanPlayer(Player):
    def __init__(self,letter):
        super().__init__(letter)
    def get_move(self,game):
        valid_square=False
        val=None
        while not valid_square:
            print(f"{self.letter}'s turn to make a move")
            square=input("Input a valid square between 0 and 8: ")
            val=int(square)
            print(game.available_moves())
            if val not in game.available_moves():
                print("Please enter a valid square")
                continue
            valid_square=True
        return val
class RandomComputerPlayer(Player):
    def __init__(self,letter):
        super().__init__(letter)
    def get_move(self,game):
        square=random.choice(game.available_moves())
        return square
class GeniusComputerPlayer(Player):
    def __init__(self,letter):
        super().__init__(letter)
    def get_move(self,game):
        if len(game.available_moves())==9:
            square=random.choice(game.available_moves())
        else:
            square=self.minimax(game,self.letter)["position"]
        return square
    def minimax(self,board_state,player):
        max_player=self.letter
        other_player="o" if player=="x" else "x"
        if board_state.current_winner==other_player:
            return {"position":None,
                    "score":1*(board_state.num_empty_squares()+1) if other_player==max_player
                    else -1*(board_state.num_empty_squares()+1)}
        elif not board_state.empty_squares():
            return{"position":None,"score":0}
        if player==max_player:
            best={"position":None,"score":-math.inf}
        else:
            best={"position":None,"score":math.inf}
        for possible_move in board_state.available_moves():
            board_state.make_move(possible_move,player)
            sim_score=self.minimax(board_state,other_player)

            board_state.board[possible_move]=" "
            board_state.current_winner=None
            sim_score["position"]=possible_move
            if player==max_player:
                if sim_score["score"]>best["score"]:
                    best=sim_score
            else:
                if sim_score["score"]<best["score"]:
                    best=sim_score
        return best


