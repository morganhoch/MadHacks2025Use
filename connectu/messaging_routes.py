# messaging_routes.py
from flask import Blueprint, session, request, redirect, url_for, render_template
from models import db, User, DirectMessage

messaging_bp = Blueprint('messaging', __name__)

@messaging_bp.route('/messages/<int:recipient_id>', methods=['GET', 'POST'])
def direct_message(recipient_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    sender = User.query.filter_by(auth0_id=session['user']['auth0_id']).first()
    recipient = User.query.get(recipient_id)
    if not recipient:
        return "Recipient not found", 404

    # Handle sending a message
    if request.method == 'POST':
        content = request.form['content']
        msg = DirectMessage(sender_id=sender.id, recipient_id=recipient.id, content=content)
        db.session.add(msg)
        db.session.commit()
        return redirect(url_for('messaging.direct_message', recipient_id=recipient.id))

    # Show chat history
    messages = DirectMessage.query.filter(
        ((DirectMessage.sender_id == sender.id) & (DirectMessage.recipient_id == recipient.id)) |
        ((DirectMessage.sender_id == recipient.id) & (DirectMessage.recipient_id == sender.id))
    ).order_by(DirectMessage.timestamp).all()
    
    return render_template('messages.html', messages=messages, recipient=recipient)
