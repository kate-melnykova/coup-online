from flask import Flask, render_template, redirect, request, flash, url_for, \
    make_response, jsonify

from models.models import Game
from models.wtforms import CreateOrJoinGameForm

app = Flask(__name__)


@app.route('/')
def main():
    form = CreateOrJoinGameForm()
    return render_template('main.html', form=form)


@app.route('/create_or_join', methods=['POST'])
def create_or_join():
    form = CreateOrJoinGameForm(request.form)
    if not form.game_id.data:
        # create a new game
        try:
            n_players = int(form.n_players.data)
        except ValueError:
            flash('Please indicate number of players')
            return redirect(url_for('main'))

        game = Game.create(n_players) # TODO: specify card types
    else:
        code = form.game_id.data
        game = Game.load(code)
        if game is None:
            flash('Game with this code does not exist')
            return redirect(url_for('main'))

    game.add_player(form.name.data)
    r = make_response(redirect(url_for('waiting')))
    r.set_cookie('COUP_name', form.name.data)
    r.set_cookie('COUP_game_id', game.id)
    return r


@app.route('/waiting', methods=['GET', 'POST'])
def waiting():
    if request.method == 'GET':
        # check if all players joined the game
        game_id = request.cookies.get('COUP_game_id')
        name = request.cookies.get('COUP_name')

        # load game with given game_id
        game = Game.load(game_id=game_id)
        if game is None:
            return redirect(url_for('main'))
        if len(game.all_users) == game.n_players:
            game.turn_id = 0
            game.save()
            return redirect(url_for('play_coup'))
        else:
            return render_template('waiting.html', game=game, name=name)

    game_id = request.cookies.get('COUP_game_id')
    # load game with given game_id
    game = Game.load(game_id=game_id)
    if game is None:
        url = url_for('main')
    elif game.turn_id > -1:
        url = url_for('play_coup')
    else:
        url = None
    return jsonify({'url': url})


@app.route('/play_coup', methods=['GET', 'POST'])
def play_coup():
    game_id = request.cookies.get('COUP_game_id')
    game = Game.load(game_id)
    if game is None:
        return redirect(url_for('main'))
    name = request.cookies.get('COUP_name')

    if request.method == 'GET':
        for user in game.all_users:
            if user.name == name:
                break
        return render_template('play_coup.html', game=game, user=user)

    # method is POST
    # move was submitted
    move = game.move
    if request.form.coup.data:
        pass






