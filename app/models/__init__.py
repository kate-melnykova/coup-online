from abc import abstractmethod
import itertools
from time import sleep
import random


class Card:
    def __init__(self, type_, owner=None):
        self.type_ = type_
        self.alive = True
        self.owner = owner

    def kill(self):
        assert self.owner is not None, 'Killing card without owner: class Card: method kill'
        self.alive = False
        self.hidden = False


class Deck:
    def __init__(self, quantity, types=['Duke', 'Ambassador', 'Assassin', 'Contessa', 'Captain']):
        self.all_cards = []
        for type_ in types:
            self.all_cards += [Card(type_)] * quantity
        self.count = quantity * len(types)
        self.shuffle()

    def shuffle(self) -> None:
        self.all_cards = random.shuffle(self.all_cards)

    def draw(self) -> 'Card' or None:
        if self.all_cards:
            self.count -= 1
            return self.all_cards.pop(0)
        else:
            return None

    def add_card(self, card):
        self.all_cards.append(Card(card.type_))
        self.count += 1
        self.shuffle()


class User:
    is_alive = property(lambda self: bool(self.cards))
    lives = property(lambda self: len(self.cards))

    def __init__(self, name, deck):
        self.name = name
        self.money = 2
        self.playing_cards = [deck.draw(), deck.draw()]
        self.killed = []

    def has_a_card(self, type_) -> int:
        """
        checks if user has a card of the given type
        :param type_: type of the card
        :return: the index of card in playing_cards or -1 if not found
        """
        for i, card in enumerate(self.playing_cards):
            if card.type == type_:
                return i
        return -1

    def replace_card(self, type_, deck):
        assert self.is_alive, 'Trying to replace card for player who already lost the game'
        i = self.has_a_card(type_)
        if i >= 0:
            card = self.playing_cards.pop(i)
            deck.add_card(card)

            card = deck.draw()
            card.owner = self.name
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
    def __init__(self, leader,
                 card_types=['Duke', 'Ambassador', 'Assassin', 'Contessa', 'Captain'],
                 quantity=3):
        self.deck = Deck(quantity=quantity)
        self.all_users = [User(leader, self.deck), ]
        self.plays = itertools.cycle(self.all_users)
        self.winner = None

    def add_user(self, username):
        self.all_users.append(User(username, self.deck))

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
