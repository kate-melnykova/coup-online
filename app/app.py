from flask import Flask, render_template, redirect, request, flash, url_for, \
    make_response

from models import Game, User, Deck
from models.wtforms import CreateOrJoinGameForm

app = Flask(__name__)


@app.route('/')
def main():
    form = CreateOrJoinGameForm()
    return render_template('main.html', form=form)


@app.route('/create_or_join', methods=['POST'])
def create_or_join():
    form = CreateOrJoinGameForm(request.form)
    if not form.join.data:
        # create a new game
        game = Game()
    else:
        code = form.join.data
        game = Game.load(code)
        if game is None:
            flash('Game with this code does not exist')
            return redirect(url_for('main'))

    game.add_player(form.name.data, form.codemaster.data)
    r = make_response(redirect(url_for('waiting')))
    r.set_cookie('codenames_name', form.name.data)
    r.set_cookie('codenames_game_id', game.id)
    return r


@app.route('/waiting', methods=['GET', 'POST'])
def waiting():
    # track who is in the team
    if request.method == 'POST':
        # user
        # we were redirected from main
        # create/join game
        form = CreateOrJoinGameForm(request.form)
        if not form.validate:
            flash('Incorrect entry')
            return redirect(url_for('main'))

        name = form.name.data
        if form.submit == 'create':
            game = Game(n_players=form.data['n_players'], dealer=name)
            user = game.all_players[0]
            all_games[game.id] = game
        else:
            # TODO try-except
            game_id = form.game_id.data
            game = all_games[game_id]
            user = game.add_player(name)

        r = make_response(render_template('create_game.html', game=game, user=user))
        r.set_cookie('COUP_name', name)
        r.set_cookie('COUP_id', game.id)
        return r
    else:
        # check if all players joined the game
        game_id = request.cookies.get('COUP_id')
        name = request.cookies.get('COUP_name')\
        # load game with given game_id
        game = Game.load(game_id=game_id)
        if len(game.all_users) == n_users:
            pass
        # TODO


@app.route('/play_coup', methods=['GET', 'POST'])
def play_coup():
    return render_template()




