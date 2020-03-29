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
    for user in game.all_users:
        if user.name == name:
            break

    if request.method == 'GET':
        if game.action.status == 4:
            # player loses life
            player = game.get_user(game.action.lose_life[0])
            if not player.playing_cards:
                print('Killing a player with no influence')
                raise
            elif len(player.playing_cards) == 1:
                player.lose_life(player.playing_cards[0])
                game.action.message += f'{player.name} has no influence now.\n'
                game.action.status = 6
        return render_template('play_coup.html', game=game, user=user)

    # method is POST
    # action/challenge/blocking/whatever was submitted
    print(f'Game status {game.action.status}')
    if game.action.status == 0:
        coup = request.form.get('coup', '')
        steal = request.form.get('steal', '')
        other = request.form.get('submit', '')
        print(f'request.form {request.form}')
        print(f'coup={coup}, steal={steal}, other={other}')
        if coup:
            print('About to coup')
            game.action.do_action(game, 'coup', coup)
        elif steal:
            print('About to steal')
            game.action.do_action(game, 'steal', steal)
        else:
            print(f'About to {other}')
            game.action.do_action(game, other)

    elif game.action.status == 4:


    elif game.action.status == 6:
        # user name was notified about action
        if name not in game.action.notified:
            game.action.notified.append(name)

        if len(game.action.notified) >= len(game.get_alive_players()):
            game.action.completed = 1
            game.next_move()

    game.save()
    return render_template('play_coup.html', game=game, user=user)






