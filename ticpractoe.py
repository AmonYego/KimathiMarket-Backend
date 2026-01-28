from game import HumanPlayer,RandomComputerPlayer,GeniusComputerPlayer
class Tictactoe:
    def __init__(self):
        self.board=[" " for i in range(9)]
        self.current_winner=None
    def print_board(self):
        rows=[self.board[i*3:(i+1)*3] for i in range(3)]
        for row in rows:
            print("/"+"/".join(row)+"/")
    def empty_squares(self):
        return " " in self.board
    def num_empty_squares(self):
        num=self.board.count(" ")
        return num
    def print_board_nums(self):
        rows=[[str(i) for i in range(j*3,(j+1)*3)] for j in range(3)]
        for row in rows:
            print("/"+"/".join(row)+"/")
    def available_moves(self):
        available_moves=[]
        for (idx,item) in enumerate(self.board):
            if item==" ":
                available_moves.append(idx)
        return available_moves
    def make_move(self,square,letter):
        if self.board[square]==" ":
            self.board[square]=letter
            if self.winner(square,letter):
                self.current_winner=letter
            return True
        return False
    def winner(self,square,letter):
        row_ind=square//3
        row=self.board[row_ind*3:(row_ind+1)*3]
        if all(spot==letter for spot in row):
            return True
        col_ind=square%3
        column=[self.board[col_ind+i*3] for i in range(3)]
        if all(spot==letter for spot in column):
            return True
        diagonal1=[self.board[i] for i in [0,4,8]]
        if all(spot==letter for spot in diagonal1):
            return True
        diagonal2 = [self.board[i] for i in [2,4,6]]
        if all(spot==letter for spot in diagonal2):
            return True
def play(game,x_player,o_player,print_game):
    if print_game:
        #game.print_board_nums()
       pass
    letter="o"
    while game.empty_squares:
        if letter=="x":
           square=x_player.get_move(game)
        else:
            square=o_player.get_move(game)

        if game.make_move(square,letter):
            #print(f"{letter} makes a move to square {square}")
            #game.print_board()
            num = game.num_empty_squares()
        if game.current_winner:
            #print(f"{letter} wins!")
            return letter
        letter="o" if letter=="x" else "x"
        if num<1 and not  game.current_winner:
            #print("Its a tie")
            break
    #print("Thanks for playing")
if __name__=="__main__":
    x_wins=0
    o_wins=0
    ties=0
    for _ in range(1000):
        t=Tictactoe()
        x_player=RandomComputerPlayer("x")
        o_player=GeniusComputerPlayer("o")
        result=play(t,x_player,o_player,print_game=False)
        if result=="x":
            x_wins+=1
        elif result=="o":
            o_wins+=1
        else:
            ties+=1
    print(f"After 1000 iterations,we see {x_wins} X wins,{o_wins} O wins and {ties} ties")
