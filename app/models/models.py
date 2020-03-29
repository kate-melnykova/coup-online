from abc import abstractmethod
from datetime import datetime
import itertools
import json
from time import sleep
from typing import List, Set
import random
from uuid import uuid4

from models.db import db


class Deck:
    mapping = {
        0: 'Duke',
        1: 'Assassin',
        2: 'Contessa',
        3: 'Captain',
        4: 'Ambassador',
    }

    @classmethod
    def reverse_mapping(cls, type_: str):
        for k, v in cls.mapping.items():
            if v == type_:
                return k

    def __init__(self, cards=[]):
        self.all_cards = cards

    @classmethod
    def create(cls, quantity, card_types=Set[int]):
        instance = cls()
        for type_ in card_types:
            instance.all_cards += [type_] * quantity
        return instance

    def draw(self) -> int or None:
        if self.all_cards:
            count = len(self.all_cards)
            return self.all_cards.pop(random.randint(0, count - 1))
        else:
            return None

    def add_card(self, type_):
        self.all_cards.append(type_)

    def serialize(self):
        return json.dumps(self.all_cards)

    @staticmethod
    def deserialize(lst: List[int]) -> List[int]:
        return Deck(cards=json.loads(lst))


class User:
    is_alive = property(lambda self: bool(self.playing_cards))
    lives = property(lambda self: len(self.playing_cards))

    def __init__(self, name, money, playing_cards, killed):
        assert len(playing_cards) + len(killed) == 2, f'User {name} has not two cards'
        assert money >= 0, f'User {name} has negative amount of money'
        self.name = name
        self.money = money
        self.playing_cards = playing_cards
        self.killed = killed

    @classmethod
    def create(cls, name, deck):
        playing_cards = [deck.draw(), deck.draw()]
        return User(name=name,
                    money=2,
                    playing_cards=playing_cards,
                    killed=[])

    def serialize(self):
        d = {
            'name': self.name,
            'money': self.money,
            'playing_cards': self.playing_cards,
            'killed': self.killed
        }
        return json.dumps(d)

    @classmethod
    def deserialize(cls, string: str) -> 'User':
        data = json.loads(string)
        return cls(**data)

    def has_a_card(self, type_: int) -> int:
        """
        checks if user has a card of the given type
        :param type_: type of the card
        :return: the index of card in playing_cards or -1 if not found
        """
        try:
            i = self.playing_cards.index(type_)
        except ValueError:
            return -1
        else:
            return i

    def replace_card(self, type_: int, deck: 'Deck'):
        assert self.is_alive, 'Trying to replace card for player who already lost the game'
        i = self.has_a_card(type_)
        if i >= 0:
            card = self.playing_cards.pop(i)
            deck.add_card(card)

            card = deck.draw()
            self.playing_cards.append(card)
        else:
            raise

    def lose_life(self, type_: int):
        assert self.is_alive, 'Trying to take a life from a player with no lifes'
        i = self.has_a_card(type_)
        if i < 0:
            raise
        else:
            card = self.playing_cards.pop(i)
            self.killed.append(card)

    def print_playing_cards(self) -> List[str]:
        return [Deck.mapping[card] for card in self.playing_cards]

    def print_killed(self) -> List[str]:
        return [Deck.mapping[card] for card in self.killed]


class Action:
    action_to_word = ['coup', 'income', 'foreign aid', 'taxes', 'steal', 'assassinate', 'ambassador']
    status_to_word = {0: 'waiting for action',
                      1: 'waiting for challenge of action',
                      2: 'waiting for blocking',
                      3: 'waiting for challenging blocking',
                      4: 'losing_life',
                      5: 'waiting for ambassador to complete his move',
                      6: 'notify all about completion',
                      7: 'completed'}

    @classmethod
    def action_to_int(cls, s: str) -> int or None:
        try:
            idx = cls.action_to_word.index(s)
        except ValueError:
            return None
        else:
            return idx

    _blocking_mapping = {
        'assassinate': ['contessa'],
        'steal': ['captain', 'ambassador'],
        'foreign aid': ['duke']
    }

    @classmethod
    def blocking_mapping_to_int(cls, action: int):
        action_word = cls.action_to_word(action)
        blocking_cards_word = cls._blocking_mapping.get(action_word, [])
        return [Deck.reverse_mapping(card_word) for card_word in blocking_cards_word]

    def action_to_str(self) -> str:
        action_to_str = [
            f'{self.action_by} coup {self.action_target}',
            f'{self.action_by} takes income',
            f'{self.action_by} foreign aid',
            f'{self.action_by} takes taxes as a Duke',
            f'{self.action_by} steals from {self.action_target}',
            f'{self.action_by} assassinates {self.action_target}',
            f'{self.action_by} acts as an ambassador'
        ]
        if self.action < 0:
            return 'Waiting for action'
        else:
            return action_to_str[self.action]

    def __init__(self, status=0, message='',
                 action=[-1, '', ''],
                 challenge_action=[0, list(), ''],
                 block = [0, ''],
                 challenge_block = [0, list(), ''],
                 lose_life = ['', ''],
                 notified=list()):
        self.action = action
        # first index: action encoding, see action_to_word
        # second index: player name who made action
        # third index: the target of action if first index is 0 (coup), 4 (steal), 5 (assassinate)

        self.challenge_action = challenge_action
        # first index: 1 if challenged, -1 if accepted, 0 is undecided
        # second index: list of user names who don't want to challenge
        # third index: if challenged, the name of person who challenges

        self.block = block
        # first index: 1 if blocked, -1 if not, 0 is undecided
        # second index: name of the card that blocks

        self.challenge_block = challenge_block
        # first index: 1 if blocking is accepted, -1 if not, 0 if undecided
        # second index: list of names of users who don't want to challenge blocking
        # third index: if challenged, name of the person who challenges

        self.lose_life = lose_life
        # first index: who loses life
        # second index: which card

        self.status = status  # integer, encoding is stored in status_to_word
        self.notified = notified  # list of all players' names who were notified of how the turn ended
        self.message = message  # is displayed to all players

    def serialize(self) -> str:
        d = dict()
        for attribute in ['action', 'challenge_action',
                          'block', 'challenge_block',
                          'lose_life', 'notified',
                          'status', 'message']:
            d[attribute] = getattr(self, attribute)
        return json.dumps(d)

    @classmethod
    def deserialize(cls, data: str) -> 'Move':
        print(f'Stored action data: {data}')
        d = json.loads(data)
        return cls(**d)

    def do_action(self, game: 'Game', value: str, target='') -> bool:
        """
        performs the action
        :param game: game that has this action
        :param value: string that represents the action. Should be in action_to_word
        :param target: name of the player who is targeted
            (required if value='coup' or 'steal', or assassinate')
        :return: True if action is possible, False otherwise
        """
        if self.status:
            return False

        encoded = self.action_to_int(value)
        if encoded is None:
            return False

        self.action = [encoded, game.cur_player, target]  # TODO: assert target is a valid player name
        if value == 'income':
            # cannot be blocked or challenged
            user = game.get_user(game.cur_player)
            user.money += 1
            self.status = 6
            self.message = f'{game.cur_player} takes income.\n'
            self.notified.append(game.cur_player)
            game.action = self
            game.save()
            return True

        if value == 'coup':
            print('Coup is happening')
            self.status = 4
            self.lose_life[0] = self.action[2]
            self.message = f'{game.cur_player} coup {self.action[2]}.\n'
            game.action = self
            game.save()

    def challenge_action(self, game: 'Game', by: str, reply: bool) -> bool:
        if game.status != 1:
            return False

        if reply:
            self.challenge_action = [1, self.challenge_action[1], by]
            self.message += f'Action was challenged by {by}.\n'
            challenged_card_map = {
                'taxes': 'Duke',
                'steal': 'Captain',
                'assassinate': 'Assassin',
                'ambassador': 'Ambassador'
            }
            card = challenged_card_map[self.action_to_word(self.action[0])]
            encoded_card = Deck.reverse_mapping(card)
            if encoded_card in User.playing_cards:
                self.message += f'Challenge found that {game.cur_player} has the {card}.\n'
                self.message += f'{ by } loses a life and {game.cur_player} gets a new card.\n'
                user = game.get_user({game.cur_player})
                user.replace_card(encoded_card)
                self.status = 4
                self.lose_life = [by, '']
            else:
                self.message += f'Challenge found that {game.cur_player} does not have the {card}.\n'
                self.message += f'{game.cur_player} loses a life.\n'
                # TODO replace card
                self.status = 4
                self.lose_life = [game.cur_player, '']
        else:
            self.challenge_action[1].append(by)
            if len(self.challenge_action == self.n_players):
                self.challenge_action[0] = -1
                self.message += f'Action is NOT challenged.\n'
                # next step is either block of perform action
                # note that if we are here, the action can be challenged
                action_word = self.action_to_word(self.action[0])
                if action_word in ['steal', 'assassinate']:
                    self.message += f'Considering blocking.\n'
                    self.status = 2
                elif action_word == 'taxes':
                    user = game.get_user(game.cur_player)
                    user.money += 3
                    self.message += f'{game.cur_player} takes three coins.'
                    self.status = 6
                    self.notified.append(game.cur_player)
                else:
                    self.message += f'{game.cur_player} selects new playing cards.\n'
                    self.status = 5
            game.save()
            return True

    def block(self, game: 'Game', by: str):
        action = self.action[0]
        if action == 'foreign aid':
            encoded_card = Deck.reverse_mapping('Duke')
            if encoded_card in User.playing_cards:
                self.message += 'Challenge found that {game.cur_player} does not have a Duke.\n'
                self.message += '{ game.cur_player } loses a life.\n'
                self.status = 4
                self.lose_life = [game.cur_player.name, '']
            else:
                self.message += 'Challenge found that {game.cur_player} has a Duke.\n'
                user = game.get_user({game.cur_player})
                user.replace_card(encoded_card)
                self.status = 4
                self.lose_life = [by, '']


class Game:
    @classmethod
    def load(cls, game_id: str) -> 'Game' or None:
        """
        loads the game with given game_id
        """
        data = db.load(game_id)
        if data is None:
            return None

        data = json.loads(data)
        instance = cls()
        instance.id = data['id']
        instance.n_players = data['n_players']
        instance.deck = Deck.deserialize(data['deck'])
        instance.all_users = [User.deserialize(user_data) for user_data in data['all_users']]
        instance.turn_id = data['turn_id']
        instance.action = Action.deserialize(data['action'])
        instance.cur_player = data['cur_player']
        instance.winner = data['winner']
        return instance

    def save(self) -> None:
        d = {
            'id': self.id,
            'n_players': self.n_players,
            'deck': self.deck.serialize(),
            'all_users': [user.serialize() for user in self.all_users],
            'turn_id': self.turn_id,
            'action': self.action.serialize(),
            'cur_player': self.cur_player,
            'winner': self.winner
        }
        d = json.dumps(d)
        db.save(self.id, d)

    @classmethod
    def create(cls, n_players,
               card_types={'Duke', 'Ambassador', 'Assassin', 'Contessa', 'Captain'}) -> 'Game':
        card_types = set(Deck.reverse_mapping(t) for t in card_types)
        if n_players < 7:
            quantity = 3
        elif n_players < 9:
            quantity = 4
        else:
            quantity = 5

        self = cls()
        self.id = str(uuid4())[:4]
        self.n_players = n_players
        self.deck = Deck.create(quantity=quantity, card_types=card_types)
        self.all_users = list()
        self.turn_id = -1
        self.action = Action()
        self.cur_player = None
        self.winner = None
        self.save()
        return self

    def add_player(self, name: str) -> None:
        user = User.create(name, self.deck)
        self.all_users.append(user)
        if len(self.all_users) == self.n_players:
            self.turn_id = 0
            self.cur_player = self.all_users[0].name
        self.save()

    def get_user(self, name: str) -> 'User' or None:
        for user in self.all_users:
            if user.name == name:
                return user
        return None

    def get_alive_players(self) -> List[str]:
        return [user.name for user in self.all_users if user.is_alive]

    def next_move(self) -> bool:
        """
        sets up the game for the next move if applicable
        :return: True if the next move is possible, False if the game is finished
        """
        alive_players = self.get_alive_players()
        if len(alive_players) == 1:
            return False

        self.turn_id += 1
        self.action = Action()
        # change cur_player
        for i, player in enumerate(self.all_users):
            if player.name == self.cur_player:
                break

        for i0 in range(i+1, self.n_players):
            name = self.all_users[i0].name
            if name in alive_players:
                self.cur_player = name
                return True

        self.cur_player = alive_players[0]
        print(f'New cur_player is {self.cur_player}')
        return True


