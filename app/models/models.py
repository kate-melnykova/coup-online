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
                      5: 'perform the action',
                      6: 'notify all about completion',
                      7: 'complete'}

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
                 block = [0, list(), '', -1],
                 challenge_block = [0, list(), ''],
                 lose_life = ['', '', 6],
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
        # second index: if action is a foreign aid, list contains a names of people who approve it
        # third index: name of the user that blocks
        # fourth index: the card that blocks

        self.challenge_block = challenge_block
        # first index: 1 if blocking is accepted, -1 if not, 0 if undecided
        # second index: list of names of users who don't want to challenge blocking
        # third index: if challenged, name of the person who challenges

        self.lose_life = lose_life
        # first index: who loses life
        # second index: which card
        # third index: action status after losing action

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
        self.challenge_action[1].append(game.cur_player)  # cur_player approves their action
        self.block[1].append(game.cur_player)  # cur_player approves their action
        user = game.get_user(game.cur_player)
        if value == 'coup':
            # cannot be blocked or challenged
            self.status = 4
            self.lose_life[0] = self.action[2]
            self.lose_life[2] = 6
            self.message = f'{game.cur_player} coup {self.action[2]}.\n'
            user.money -= 7

        elif value == 'income':
            # cannot be blocked or challenged
            user.money += 1
            self.status = 6
            self.message = f'{game.cur_player} takes income.\n'
            self.notified.append(game.cur_player)

        elif value == 'foreign aid':
            self.status = 2
            self.message = f'''{game.cur_player} wants to take foreign aid.\n'''

        elif value == 'taxes':
            self.status = 1
            self.message = f'''{game.cur_player} wants to take taxes as a Duke.\n'''

        elif value == 'steal':
            self.status = 1
            self.message = f'''{game.cur_player} wants to steal from {self.action[2]} as a Captain.\n'''

        elif value == 'assassinate':
            self.status = 1
            self.message = f'''{game.cur_player} wants to assassinate {self.action[2]} as an Assassin.\n'''

        elif value == 'ambassador':
            self.status = 1
            self.message = f'''{game.cur_player} wants to exchange cards as an Ambassador.\n'''

        game.save()
        return True

    def do_challenge_action(self, game: 'Game', by: str, reply: bool) -> bool:
        if self.status != 1:
            return False

        if reply:
            self.challenge_action = [1, self.challenge_action[1], by]
            self.message += f'''Action was challenged by {by}.\n'''
            challenged_card_map = {
                'taxes': 'Duke',
                'steal': 'Captain',
                'assassinate': 'Assassin',
                'ambassador': 'Ambassador'
            }
            card = challenged_card_map[self.action_to_word[self.action[0]]]
            encoded_card = Deck.reverse_mapping(card)
            user = game.get_user(game.cur_player)
            if encoded_card in user.playing_cards:
                self.message += f'''Challenge found that {game.cur_player} has the {card}.\n'''
                self.message += f'{ by } loses a life and {game.cur_player} gets a new card.\n'
                user.replace_card(encoded_card, game.deck)
                self.status = 4
                # determine what happens after losing life
                blockable_actions = [self.action_to_int(a) for a in ['steal', 'assassinate']]
                if self.action[0] in blockable_actions:
                    self.lose_life = [by, '', 2]
                else:
                    self.lose_life = [by, '', 5]
            else:
                self.message += f'''Challenge found that {game.cur_player} does not have the {card}.\n'''
                self.message += f'{game.cur_player} loses a life.\n'
                # TODO replace card
                self.status = 4
                self.lose_life = [game.cur_player, '', 6]
        else:
            if by not in self.challenge_action[1]:
                self.challenge_action[1].append(by)
            if len(self.challenge_action[1]) == len(game.get_alive_players()):
                self.challenge_action[0] = -1
                self.message += f'Action is NOT challenged.\n'
                # next step is either block of perform action
                # note that if we are here, the action can be challenged
                action_word = self.action_to_word[self.action[0]]
                if action_word in ['steal', 'assassinate']:
                    self.message += f'Considering blocking.\n'
                    self.status = 2
                elif action_word == 'taxes':
                    self.status = 5
                else:
                    self.message += f'{game.cur_player} selects new playing cards.\n'
                    self.status = 7
            game.save()
            return True

    def do_block(self, game: 'Game', reply: bool, by_user='', by_card=-1):
        """
        Performs blocking if requested
        :param game: current game instance
        :param reply: True if blocking occurs False otherwise
        :param by_user: username who sends reply
        :param by_card: card that blocks the action, required to be a card name if reply is True
        :return:
        """
        if reply:
            # TODO: verify that by_card can block action
            self.block = [1, self.block[1], by_user, by_card]
            self.message += f'''{by_user} blocks action using {game.deck.mapping[by_card]}.\n'''
            self.status = 3
            game.save()

        elif self.action_to_word[self.action[0]] == 'foreign aid':
            if by_user not in self.block[1]:
                self.block[1].append(by_user)

            if len(self.block[1]) == len(game.get_alive_players()):
                self.message += f'''Action is not blocked.\n'''
                action_word = self.action_to_word[self.action[0]]
                if action_word == 'assassinate':
                    self.status = 4
                    self.lose_life = [self.action[2], '', 6]
                elif action_word == 'ambassador':
                    self.status = 7
                else:
                    self.status = 5
            game.save()

    def do_challenge_block(self, game: 'Game', reply: bool, by: str) -> bool:
        """
        checks if block is challenged, and if so, performs challenge
        :param game: instance of the currently played game
        :param reply: True if the user challenges block, False otherwise
        :param by: name of the player who submits reply
        :return: True if game continues, False otherwise
        """
        if reply:
            self.challenge_block = [1, self.challenge_block[1], by]
            blocking_card = self.block[3]
            blocking_card_name = game.deck.mapping[blocking_card]
            blocking_name = self.block[2]
            blocking_user = game.get_user(blocking_name)
            challenger_user = game.get_user(by)
            self.message += f'''{by} challenged that {blocking_name} has {blocking_card_name}.\n'''
            if blocking_card in blocking_user.playing_cards:
                self.message += f'''The challenge found that {blocking_name} has {blocking_card_name}.\n'''
                self.message += f'''{by} loses a life and {blocking_name} gets a new card.\n'''
                self.message += f'''The original move is blocked. Waiting for {by} to discard a card.\n'''
                blocking_user.replace_card(blocking_card, game.deck)
                self.status = 4
                self.lose_life = [by, '', 6]
            elif self.action_to_word[self.action[0]] == 'assassinate':
                self.message += f'''The challenge found that {blocking_name} does NOT have {blocking_card_name}.\n'''
                self.message += f'''{blocking_name} loses all their influence.'''
                blocking_user.killed += blocking_user.playing_cards
                blocking_user.playing_cards = []
                self.status = 6
            else:
                # stealing and taxes are currently the only options
                self.message += f'''The challenge found that {blocking_name} does NOT have {blocking_card_name}.\n'''
                self.message += f'''The original action goes through. {blocking_name} loses one of their influence.\n'''
                self.message += f'''Waiting for {blocking_name} decision.\n'''
                self.lose_life = [blocking_name, '', 5]
        elif self.action_to_word[self.action[0]] == 'ambassador':
            if by not in self.challenge_block[1]:
                self.challenge_block[1].append(by)

            if len(self.challenge_block[1]) == len(game.get_alive_players()):
                self.message += f'''The block is not challenged. The original action is blocked.\n'''
                return game.next_move()
        else:
            self.message += f'''The block is not challenged. The original action is blocked.\n'''
            return game.next_move()

    def do_lose_life(self, game: 'Game', type_: int):
        name = self.lose_life[0]
        user = game.get_user(name)
        user.lose_life(type_, game.deck)
        self.status = self.lose_life[2]
        self.message += f'''{name} loses the influence {game.deck.mapping[type_]}.\n'''


    def do_perform_action(self, game: 'Game') -> bool:
        if self.status != 5:
            return False

        action = self.action_to_word[self.action[0]]
        user = game.get_user(game.cur_player)
        if action == 'coup':
            # do couping, currently never achieved
            # because redirected to lose_life
            raise
        elif action == 'income':
            user.money += 1
            # currently not achievable, will be used later
            self.message += f'{game.cur_player} takes income.'
            self.status = 6
        elif action == 'foreign aid':
            user.money += 2
            self.message += f'{game.cur_player} gets foreign aid.'
            self.status = 6
        elif action == 'taxes':
            user.money += 3
            self.message += f'{game.cur_player} gets taxes.'
            self.status = 6
        elif action == 'steal':
            user.money += 2
            target_name = self.action[2]
            target = game.get_user(target_name)
            if target.is_alive:
                target.money = max(target.money - 2, 0)
            self.message += f'{game.cur_player} steals from {self.action[2]}.'
            self.status = 6
        elif action == 'assassinate':
            self.message += f'{game.cur_player} assassinates {self.action[2]}.\n'
            self.status = 4
            game.lose_life[0] = self.action[2]  # who loses life
            game.lose_life[2] = 6  # move is completed
            self.notified = [self.action[2], game.cur_player, ]
        elif action == 'ambassador':
            self.message += f'{game.cur_user} exchanges cards. Waiting for his/her decision.\n'
            self.status = 7
        game.save()

    def do_notify(self, game: 'Game', name: str) -> bool:
        """
        records that user with username name got notification
        :param game: instance of currently played game
        :param name: name of the user
        :return: True if game continues False otherwise
        """
        if name in game.get_alive_players() and name not in self.notified:
            self.notified.append(name)

        game.save()
        if len(self.notified) == len(game.get_alive_players()):
            return game.next_move()

        return True


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


