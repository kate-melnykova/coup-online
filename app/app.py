from flask import Flask, render_template, redirect

from models import Game, User, Deck, Card

app = Flask(__name__)


@app.route('/')
def main():
    return render_template('main.html')


@app.route('/game', methods=['GET', 'POST'])
def game():
    game = Game(['Andrey', 'Kate'])
    return render_template('game.html', game=game)





