import time

from flask import Flask, render_template, redirect, request, flash, url_for, \
    make_response, jsonify

from models.models import Game
from models.wtforms import CreateOrJoinGameForm

app = Flask(__name__)

events = dict()


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

        game = Game.create(n_players)  # TODO: specify card types
    else:
        code = form.game_id.data
        game = Game.load(code)
        if game is None:
            flash('Game with this code does not exist')
            return redirect(url_for('main'))

    if form.name.data not in game.all_users:
        game.add_player(form.name.data)
        r = make_response(redirect(url_for('waiting')))
        r.set_cookie('COUP_name', form.name.data)
        r.set_cookie('COUP_game_id', game.id)
        return r
    else:
        flash('This name is taken by your teammate. Please select another one.')
        return redirect(url_for('main.html'))


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
    user = game.get_user(name)

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
                game.action.status = game.action.lose_life[2]
        if game.action.status == 5:
            game.action.do_perform_action(game)

        if len(game.get_alive_players()) == 1:
            return redirect(url_for('winning'))

        return render_template('play_coup.html', game=game, user=user)

    # method is POST
    # action/challenge/blocking/whatever was submitted
    print(f'Game status {game.action.status}')
    if game.action.status == 0:
        coup = request.form.get('coup', '')
        steal = request.form.get('steal', '')
        assassinate = request.form.get('assassinate', '')
        other = request.form.get('submit', '')
        print(f'request.form {request.form}')
        print(f'coup={coup}, steal={steal}, other={other}')
        if coup:
            game.action.do_action(game, 'coup', coup)
        elif steal:
            game.action.do_action(game, 'steal', steal)
        elif assassinate:
            game.action.do_action(game, 'assassinate', assassinate)
        else:
            game.action.do_action(game, other)

    elif game.action.status == 1:
        is_challenged = request.form['challenge']
        is_challenged = True if is_challenged == 'yes' else False
        game.action.do_challenge_action(game, name, is_challenged)

    elif game.action.status == 2:
        value = request.form['block']
        if value == 'no':
            game.action.do_block(game, False, name)
        elif value == 'yes':
            action_word = game.action.action_to_word[game.action.action[0]]
            if action_word == 'assassinate':
                card = game.deck.reverse_mapping('Contessa')
            elif action_word == 'foreign aid':
                card = game.deck.reverse_mapping('Duke')
            game.action.do_block(game, True, name, card)
        else:
            card = game.deck.reverse_mapping(value)
            game.action.do_block(game, True, name, card)

    elif game.action.status == 3:
        reply = request.form['submit']
        reply = True if reply == 'yes' else False
        game.action.do_challenge_block(game, reply, name)

    elif game.action.status == 4:
        # TODO move it under the Action class as a function and call it
        if game.action.lose_life[0] == name:
            card_name = request.form['to_kill']
            card_type = game.deck.reverse_mapping(card_name)
            user.lose_life(card_type)
            # life can be lost either via assassination
            game.action.status = game.action.lose_life[2]

    elif game.action.status == 5:
        game.action.do_perform_action(game)

    elif game.action.status == 7:
        selected_cards = [int(c) for c in request.form.getlist('card')]
        discarded = game.action.ambassador_cards[:2 + len(user.playing_cards)]
        for c in selected_cards:
            discarded.remove(c)
        user.playing_cards = selected_cards
        for c in discarded:
            game.deck.add_card(c)
        game.action.status = 6

    elif game.action.status == 6:
        # user name was notified about action
        if name not in game.action.notified:
            game.action.notified.append(name)

        if len(game.action.notified) >= len(game.get_alive_players()):
            game.action.completed = 1
            is_continued = game.next_move()
            if not is_continued:
                game.save()
                return redirect(url_for('winning'))

    game.save()
    for user_ in game.all_users:
        events[f'{game_id}:{user_.name}'] = {'type': 'reload',
                                             'data': {
                                                 'url': url_for('play_coup'),
                                             }
                                             }
    return render_template('play_coup.html', game=game, user=user)


@app.route('/winning')
def winning():
    game_id = request.cookies.get('COUP_game_id')
    game = Game.load(game_id)
    if game is None:
        return redirect(url_for('main'))
    name = request.cookies.get('COUP_name')
    for user in game.all_users:
        if user.name == name:
            break
    return render_template('winning.html', game=game, user=user)


@app.route('/long_polling')
def long_polling():
    game_id = request.cookies.get('COUP_game_id')
    game = Game.load(game_id)
    if game is None:
        return redirect(url_for('main'))

    name = request.cookies.get('COUP_name')
    event_target = f'{game_id}:{name}'

    while True:
        event = get_event(event_target)
        if event:
            return jsonify(event)
        time.sleep(1)


def get_event(event_target):
    try:
        return events.pop(event_target)
    except KeyError:
        return None


@app.route('/logo')
def logo():
    return



