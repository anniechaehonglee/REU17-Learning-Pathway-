import log_analyzer
import regex
import util
import sys
import os

import pandas as pd
import numpy as np

class stashedInformation():
    def __init__(self,
                 action,
                 current_index,
                 next_index,
                 correctness,
                 start_time,
                 closed_time,
                 temp_log,
                 temp_corr):

        self._action = action                #list
        self._current_index = current_index  #2d list
        self._next_index = next_index        #2d list
        self._correctness = correctness      #2d list
        self._start_time = start_time        #list
        self._closed_time = closed_time      #list
        self._temp_log = temp_log            #element
        self._temp_corr = temp_corr          #element

class StudyLogAnalyzer(log_analyzer.LogAnalyzer):
    #Annie's study log analyer:
    #this study analyzer preprocesses and prints data at the end of a puzzle
    #processed data is logged into a data tree named stashedInformation

    def _setup(self):
        # instantiate dataframe
        # declaring columns here will ensure they appear before other columns
        self.full_df = pd.DataFrame()

    def _get_regex_list(self):
        # return a list of tuples
        # the first element is a regex object, the second is a function callback
        return [
            (regex.CHECK_OPENED_PROJECT, self.__opened_project),
            (regex.CHECK_PUZZLE_BREAKDOWN, self.__puzzle_breakdown),
            (regex.CHECK_PUZZLE_CODE, self.__puzzle_code),
            (regex.CHECK_PUZZLE_COMPARISON, self.__puzzle_correctness),
            (regex.CHECK_PUZZLE_PLAYED, self.__puzzle_played),
            (regex.CHECK_PUZZLE_PANE_CLOSED, self.__pane_closed),
            (regex.CHECK_MENTAL_EFFORT, self.__mental_effort)
        ]

    def finish(self):
        # we save a .csv containing every user
        filename = os.path.join(self.data_directory, 'full-process.csv')
        self.full_df.to_csv(filename, index=False)

    def _pre_analysis(self):
        # new logfile
        self.current_puzzle = None
        self.df = pd.DataFrame(
            columns=[
                'codename',
                'puzzle',
                'action',
                'current_index',
                'next_index',
                'correctness',
                'start_time',
                'closed_time'
            ]
        )
        self.username = self.directory

    def _post_analysis(self):
        # we save a .csv for each user
        self.df = self.df.fillna(0)
        self.full_df = self.full_df.append(self.df, ignore_index=True)

        filename = os.path.join(self.data_directory, '{0}-process.csv'.format(self.username))
        self.df.to_csv(filename, index=False)

    def _new_puzzle(self, puzzle, millis):
        if self.current_puzzle is not None:
            self._quit_puzzle()
        self.current_puzzle = puzzle
        self.start_time = millis
        self.action = []
        self.play_time = []
        self.temp_closed = []

    def _end_puzzle(self, record, millis):
        self.end_time = millis
        self.current_puzzle = None

    def _quit_puzzle(self):
        self.current_puzzle = None

    def _add_row(self, record, action = None,
                current_index = None,
                next_index = None,
                correctness = None,
                start_time = None,
                closed_time = None):
        if self.current_puzzle is None:
            return

        # add puzzle data to our dataframe
        row = {
            'codename': self.directory,
            'puzzle': self.current_puzzle,
            'action': action,
            'current_index': current_index,
            'next_index': next_index,
            'correctness': correctness,
            'start_time': start_time,
            'closed_time': closed_time
        }
        self.df = self.df.append(row, ignore_index=True)

    def _get_time(self, record):
        # type: (log_parser.RecordInfo) -> int
        return int((int(record.properties['millis']) - self.opened_time) / 1000.)

    """ regex functions """
    def __opened_project(self, record, index):
        match = regex.REGEX_PUZZLE_PROJECT.match(record.properties['message'])
        self.opened_time = int(record.properties['millis'])
        self.stashed = stashedInformation(
                action = [],                      #initially, there is no stashed information
                current_index = [],
                next_index = [],
                correctness = [],
                start_time = [],
                closed_time = [],
                temp_log = [],
                temp_corr = [])

        if match is not None:
            self._new_puzzle(match.group(1), int(record.properties['millis']))

    #this records the answer stmts
    def __puzzle_breakdown(self, record, index):
        match = regex.REGEX_PUZZLE_BREAKDOWN.match(record.properties['message'])
        if match is not None:
            self.correct_ordering = util.parse_puzzle_code(match.group(3))
            self.solution_stmts = util.parse_blocks_sol(match.group(3))
            self.number_of_stmt = len(self.correct_ordering)

    #this records the current ordering of the stmts
    def __puzzle_code(self, record, index):
        match = regex.REGEX_PUZZLE_CODE.match(record.properties['message'])
        if match is not None:
            current_ordering = util.parse_puzzle_code(match.group(1))

        #goes through nested loop to find current ordering of the stmts
        solution_mapping = [-2] * int(self.number_of_stmt)
        for x in range(0, int(len(current_ordering))):
            for y in range(0, int(self.number_of_stmt)):
                if self.correct_ordering[y].hash == current_ordering[x].hash:
                    solution_mapping[y] = x
                    break
            else:
                continue

        self.stashed.temp_log = solution_mapping

    #this records the correctness as it is shown while the puzzle plays
    def __puzzle_correctness(self, record, index):
        correctness_mapping = ["UNKNOWN"] * int(self.number_of_stmt)
        correctness_individual = [];
        for match in regex.REGEX_PUZZLE_COMPARISON_LINES.finditer(record.properties['message']):
            correctness_individual.append(match.group(2))
        correctness_individual.pop(0) #gets rid of 'do in order'
        for x in range(0, min(int(self.number_of_stmt), len(correctness_individual))):
            correctness_mapping[x] = correctness_individual[x]
        self.stashed.temp_corr = correctness_mapping

    #this records time and play type
    def __puzzle_played(self, record, index):
        action = regex.REGEX_PUZZLE_PLAYED.match(record.properties['message']).group(1)
        self.action.append(action)
        self.play_time.append(self._get_time(record))
        self.temp_closed.append(-1)

    #this prints data when the play window closes
    def __pane_closed(self, record, index):
        self.temp_closed[-1] = self._get_time(record)
        for x in range(0, len(self.action)):
            self.stashed._action.append(self.action[x])
            self.stashed._current_index.append(self.stashed.temp_log)
            self.stashed._next_index.append(self.stashed.temp_log)
            self.stashed._correctness.append(self.stashed.temp_corr)
            self.stashed._start_time.append(self.play_time[x])
            self.stashed._closed_time.append(self.temp_closed[x])

        self.action = []
        self.play_time = []
        self.temp_closed = []

    def __mental_effort(self, record, index):
        match = regex.REGEX_MENTAL_EFFORT.match(record.properties['message'])
        if match is not None:
            self.mental_effort = util.MENTAL_EFFORT_MAPPING[match.group(1)]

        #first, duplicate the last status into next_index
        self.stashed._next_index.append(self.stashed._next_index[-1])
        #next, pop the first element in the next_index
        del self.stashed._next_index[0]
        #then for every play print:
            #play -- current -- next -- correctness -- start -- closed

        for x in range(0, len(self.stashed._action)):
            string_current = ""
            string_next = ""
            string_correctness = ""
            for y in range(0, int(self.number_of_stmt)):
                string_current += str(self.stashed._current_index[x][y]+1) + "/"
                string_next += str(self.stashed._next_index[x][y]+1) + "/"
                if self.stashed._correctness[x][y] == "CORRECT":
                    temp = "C"
                elif self.stashed._correctness[x][y] == "INCORRECT":
                    temp = "I"
                elif self.stashed._correctness[x][y] == "UNKNOWN":
                    temp = "U"
                else:
                    temp = ""
                string_correctness += temp + "/"
            self._add_row(record,
                        action = self.stashed._action[x],
                        current_index = string_current,
                        next_index = string_next,
                        correctness = string_correctness,
                        start_time = self.stashed._start_time[x],
                        closed_time = self.stashed._closed_time[x])

        self._add_row(record,
                    action = "END",
                    current_index = self.solution_stmts,
                    next_index = self.mental_effort,
                    correctness = self.number_of_stmt,
                    closed_time = self._get_time(record))

        self._end_puzzle(record, int(record.properties['millis']))

class TestAnalyzer(log_analyzer.LogAnalyzer):

    def _setup(self):
        print('TestAnalyzer: _setup')

    def _get_regex_list(self):
        print('TestAnalyzer: _get_regex_list')
        return [(regex.CHECK_OPENED_PROJECT, self._on_project_opened)]

    def _pre_analysis(self):
        print('TestAnalyzer: _pre_analysis')

    def _post_analysis(self):
        print('TestAnalyzer: _post_analysis')

    def finish(self):
        print('TestAnalyzer: finish')

    """ Methods for specific message types """

    def _on_project_opened(self, record, index):
        print('TestAnalyzer: project opened')
class EmptyAnalyzer(log_analyzer.LogAnalyzer):

    def _setup(self):
        pass

    def _get_regex_list(self):
        return []

    def _pre_analysis(self):
        pass

    def _post_analysis(self):
        pass

    def finish(self):
        pass
