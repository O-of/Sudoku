from typing import Tuple, List, Iterator
import enum
import time


class SudokuCellReturnValues(enum.Enum):
    ALREADY_FILLED: int = -1
    ZERO_VALUES: int = 0
    ONE_VALUE: int = 1
    MULTIPLE_VALUES: int = 2


class SudokuCell(object):
    """
    A cell in a Sudoku Board
    """

    def __init__(self, master: 'SudokuBoard', number: int, position: Tuple[int, int]):
        self.number = number  # Number of the square - 0 if default
        self.master = master  # Parent Board
        self.position = position  # (row, column)
        self.possible_numbers = set()  # Blank set for future use

    def __str__(self):
        return str(self.number)

    def get_indexes(self) -> Tuple[int, int, int]:
        """
        Returns the index of itself in its master's groupings
        """
        row_index, column_index = self.position
        box_index = row_index // 3 * 3 + column_index // 3

        return row_index, column_index, box_index

    def solve_this_cell(self):
        """
        Looks through the possible numbers the current cell can have; returns how many there are
        If 0: return 0
        If 1: change the number, update row/column/box, return 1
        If 2+: return 2+
        """

        if self.number != 0:  # Need to make sure that the current cell needs to be filled in
            return SudokuCellReturnValues.ALREADY_FILLED

        row_index, column_index, box_index = self.get_indexes()

        # Grabs the possible numbers
        self.possible_numbers = set(range(1, 10)).intersection(self.master.rows[row_index].valid_numbers,
                                                               self.master.columns[column_index].valid_numbers,
                                                               self.master.boxes[box_index].valid_numbers)

        # Does logic on the result
        if len(self.possible_numbers) == 1:
            self.number = next(iter(self.possible_numbers))
            self.master.rows[row_index].eliminate_numbers()
            self.master.columns[column_index].eliminate_numbers()
            self.master.boxes[box_index].eliminate_numbers()
            return SudokuCellReturnValues.ONE_VALUE
        elif len(self.possible_numbers) == 0:
            return SudokuCellReturnValues.ZERO_VALUES
        else:
            return SudokuCellReturnValues.MULTIPLE_VALUES


class SudokuSet(object):
    """
    A Set(Row/Column/Box) in a Sudoku Board
    """

    def __init__(self, master: 'SudokuBoard', squares: List[SudokuCell]):
        self.squares = squares  # All the squares in the current set
        self.master = master  # Parent Board
        self.valid_numbers = set(range(1, 10))  # Set of valid numbers for future use

    def eliminate_numbers(self):
        """
        Goes through each square and takes them out of the possibilities
        """
        for square in self.squares:
            try:
                self.valid_numbers.remove(square.number)
            except KeyError:
                pass


class SudokuBoard(object):
    """
    A Sudoku Board
    """

    def __init__(self, inpt_board: str, tree_node: 'SudokuTreeNode'):
        temp_board = inpt_board.split('\n')

        # Internal Representation of the board
        self.board: List[List[SudokuCell]] = [
            [SudokuCell(self, int(temp_board[row][column]), (row, column)) for column in range(9)] for row in
            range(9)]
        self.rows: List[SudokuSet] = [SudokuSet(self, row) for row in self.board]
        self.columns: List[SudokuSet] = [SudokuSet(self, [row[column] for row in self.board]) for column in range(9)]
        self.boxes: List[SudokuSet] = [SudokuSet(self,
                                                 [self.board[row_selection * 3 + row][column_selection * 3 + column] for
                                                  row in range(3)
                                                  for column in range(3)]) for row_selection in range(3) for
                                       column_selection in
                                       range(3)]

        self.tree_node = tree_node
        self.multi_possibility_cells: List[SudokuCell] = []

    def get_str_rep_of_board(self) -> str:
        return '\n'.join([''.join(map(str, row)) for row in self.board])

    def do_one_iteration(self):
        """
        Does one iteration out of the xx amount left
        1. clear old cached data
        2. Iterate through the cells
        3. For each cell, call solve_this_cell()
        4. If filled: pass - If zeros: stop - if one: set change_in_board to true - if 2+: add to list of multi cells
        5. return if there is a change in the board
        """
        self.multi_possibility_cells = []
        change_in_board = False

        for row in self.board:
            for cell in row:
                result = cell.solve_this_cell()

                if result == SudokuCellReturnValues.ALREADY_FILLED:
                    continue
                elif result == SudokuCellReturnValues.ZERO_VALUES:
                    return result
                elif result == SudokuCellReturnValues.ONE_VALUE:
                    change_in_board = True
                elif result == SudokuCellReturnValues.MULTIPLE_VALUES:
                    self.multi_possibility_cells.append(cell)

        return change_in_board

    def establish_child_tree_nodes(self) -> Iterator['SudokuTreeNode']:
        """
        Generator for child nodes
        1. Get the cell with lowest possibilities
        2. Make a duplicate of current board with new node associated with it
        3. Change the value of selected cell to a guess
        """

        lowest, cell_position, possibilities = 10, (-1, -1), set()

        for cell in self.multi_possibility_cells:
            if len(cell.possible_numbers) < lowest:
                lowest, cell_position, possibilities = len(cell.possible_numbers), cell.position, cell.possible_numbers

        row, column = cell_position

        for possibility in possibilities:
            temp_tree_node = SudokuTreeNode(self.tree_node.depth + 1)
            temp_tree_node.set_current_board(SudokuBoard(self.get_str_rep_of_board(), temp_tree_node))
            temp_tree_node.get_current_board().board[row][column].number = possibility
            yield temp_tree_node

    def solve_board(self) -> None:
        """
        Solves the board
        1. While there are changes, continue trying to fill in obvious numbers
        2. Check to see if done
        3. If done, put it in solved boards array, stop
        4. If not done, call establish_child_tree_nodes and add that to the current node's child nodes
        5. For each child node call solve_board
        """
        for sudoku_set in self.rows + self.columns + self.boxes:
            sudoku_set.eliminate_numbers()

        result = True
        while result:

            result = self.do_one_iteration()
            if result == SudokuCellReturnValues.ZERO_VALUES:
                return None

        board = self.get_str_rep_of_board()

        if '0' not in board:
            self.tree_node.solved_boards.append(board)
        else:
            assert len(self.multi_possibility_cells) > 0
            for child_board in self.establish_child_tree_nodes():
                self.tree_node.child_boards.append(child_board)
            for child_board in self.tree_node.child_boards:
                child_board.current_board.solve_board()

        return None


class SudokuTreeNode(object):
    """
    A Sudoku Tree Node
    """

    solved_boards = []

    def __init__(self, depth: int):
        self.child_boards: List[SudokuTreeNode] = []  # All the child boards
        self.current_board: SudokuBoard = None  # The board associated with the node
        self.depth = depth  # The depth of the current node

    def set_current_board(self, board: SudokuBoard):
        """
        Sets the board associated with the node
        """
        self.current_board = board

    def get_current_board(self) -> SudokuBoard:
        """
        Gets the board associated with the node
        """
        return self.current_board

    def find_total_nodes(self) -> int:
        """
        Travel function to determine how many nodes there are in total
        """
        if len(self.child_boards) == 0:
            return 1
        return sum([board.find_total_nodes() for board in self.child_boards])


class SudokuSolverApplication(object):
    """
    Application class for the Sudoku Solver
    """

    def __init__(self, inpt_board: str):
        self.root_node = SudokuTreeNode(0)  # The root node of the entire tree
        self.root_node.set_current_board(
            SudokuBoard(inpt_board, self.root_node))  # Associates the base board with this node
        self.time = 0  # Variable to store total time

    def solve(self):
        """
        Solves the inputted board
        """
        start = time.time()
        self.root_node.get_current_board().solve_board()
        self.time = time.time() - start

    def print_solutions(self):
        """
        Prints the boards and some extra statistics
        """
        length = len(self.root_node.solved_boards)
        print(
            f'There {"is" if length == 1 else "are"} {length}',
            f'solution{"" if length == 1 else "s"}{"" if length == 0 else ":"}')

        for board in self.root_node.solved_boards:
            print(board + '\n')

        print(f'There were a total of {self.root_node.find_total_nodes()} nodes in the tree')
        print(f'It took {self.time} seconds to finish')


solver = SudokuSolverApplication(open('sudoku_board.txt', 'r').read())
solver.solve()
solver.print_solutions()