from abc import abstractmethod
from datetime import datetime
import itertools
import json
from time import sleep
from typing import List
import random

from models.db import db


class Deck:
    mapping = {
        0: 'Duke',
        1: 'Assassin',
        2: 'Contessa',
        3: 'Captain',
        4: 'Ambassador',
    }

    def reverse_mapping(self, type_):
        for k, v in self.mapping:
            if v == 'type_':
                return k

    def __init__(self, cards=[]):
        self.all_cards = cards

    @classmethod
    def create(cls, quantity, types=['Duke', 'Ambassador', 'Assassin', 'Contessa', 'Captain']):
        instance = cls()
        for type_ in types:
            encoded = cls.reverse_mapping(type_)
            instance.all_cards += [encoded] * quantity
        return instance

    def draw(self) -> int or None:
        if self.all_cards:
            count = len(self.all_cards)
            return self.all_cards.pop(random.randint(0, count - 1))
        else:
            return None

    def add_card(self, type_):
        self.all_cards.append(type_)

    def to_db(self):
        return json.dumps(self.all_cards)

    @staticmethod
    def to_python(string: str) -> List[int]:
        return Deck(cards=json.loads(string))


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

    def to_db(self):
        d = {
            'name': self.name,
            'money': self.money,
            'playing_cards': self.playing_cards,
            'killed': self.killed
        }
        return json.dumps(d)

    @classmethod
    def to_python(cls, string: str) -> 'User':
        return cls(**string)

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


class Game:
    """
    self.challenged = 0  is no
    self.challenged = 1 is pending
    """

    def __init__(self, n_players, card_types, deck, all_users,
                 turn_id, move, cur_player, winner):
        self.n_players = n_players
        self.card_types = card_types
        self.deck = deck
        self.all_users = all_users
        self.turn_id = turn_id
        self.move = move
        self.cur_player = cur_player
        self.winner = winner

    @classmethod
    def load(cls, game_id: str) -> 'Game':
        data = db.load(game_id)
        if data is None:
            return None

        data = json.loads(data)
        return cls(data)

    def save(self) -> None:
        d = {
            'n_players': self.n_players,
            'card_types': self.card_types,
            'deck': self.deck.to_db(),
            'all_users': [user.to_db() for user in self.all_users],
            'turn_id': self.turn_id,
            'move': self.move,
            'cur_player': self.cur_player.to_db(),
            'winner': self.winner
        }
        d = json.dumps(d)
        db.save(self.game_id, d)

    def create(self, n_players,
               card_types=['Duke', 'Ambassador', 'Assassin', 'Contessa', 'Captain']):
        self.n_players = n_players
        self.card_types = [Deck.reverse_mapping(type_) for type_ in card_types]
        if n_players < 7:
            quantity = 3
        elif n_players < 9:
            quantity = 4
        else:
            quantity = 5
        self.deck = Deck.create(quantity=quantity, card_types=card_types)
        self.all_users = list()
        self.turn_id = -1
        self.move = None
        self.cur_player = None
        self.winner = None
        self.save()

    def add_player(self, name: str) -> None:
        user = User(name, self.deck)
        self.all_users.append(user)
        if len(self.all_users) == self.n_players:
            self.turn_id = 0
        self.save()

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
