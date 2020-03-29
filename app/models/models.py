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
    is_alive = property(lambda self: bool(self.cards))
    lives = property(lambda self: len(self.cards))

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

    def replace_card(self, type_, deck):
        assert self.is_alive, 'Trying to replace card for player who already lost the game'
        i = self.has_a_card(type_)
        if i >= 0:
            card = self.playing_cards.pop(i)
            deck.add_card(card)

            card = deck.draw()
            self.playing_cards.append(card)
        else:
            raise

    def lose_life(self, type_):
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


class Move:
    def __init__(self, type_= None, value=-1):
        if type_ is None:
            self.move = -1
            self.blocked = -1
            self.challenged = []
        elif type_ == 'move':
            self.move = value
            # TODO
        elif type_ == 'blocked':
            self.blocked = value
        elif type_ == 'challenged':
            self.challenged.append(value)
            # TODO

    def serialize(self) -> str:
        d = [self.move, self.blocked, self.challenged]
        return json.dumps(d)

    @classmethod
    def deserialize(cls, data: str) -> 'Move':
        d = json.loads(data)
        self = cls()
        self.move, self.blocked, self.challenged = d
        return self


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
        instance.move = Move.deserialize(data['move'])
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
            'move': self.move.serialize(),
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
        self.move = Move()
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

    '''
    def challenge_to_have(self, user_accused, user_accuses, type_) -> bool:
        """
        User_accuses challenges user_accused to have a card of type_
        :return: true if the original claim is supported and false otherwise
        """
        i = user_accused.has_a_card(type_)
        if i >= 0:
            # claim is backed-up
            print(f'{self.name} has {type_}')
            user_accused.replace_card()
            self.lose_one_life(user_accuses)
            return True
        else:
            print(f'{user_accused.name} does not have {type_}')
            self.lose_one_life(user_accused)
            return False

    def play(self, action, towards=None):
        if self.winner is not None:
            return f'{self.winner} won'

        # select user
        user = next(self.plays)
        if action == 'Income':
            print(f'{self.name}: I take income')
            self.money += 1

        elif action == 'Foreign aid':
            print(f'{self.name}: I take a foreign aid')
            print('Waiting for Dukes to block...')
            # wait
            # TODO

        elif action == 'Taxes':
            print(f'{self.name}: I am a Duke and I collect taxes. Challenge? Y/n')
            # ask if challenged
            # TODO
            user_accuses = input()
            if user_accuses:
                supported = self.challenge_to_have(user, user_accuses, 'Duke')
                if supported:
                    user.money += 3
            else:
                user.money += 3

        winner = self.is_winner()
        if winner is not None:
            print(f'')
        self.play()
    '''
