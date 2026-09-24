from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config import Config
from app.logging_setup import configure_logging
from app.utilities.ca_bundle import ensure_ca_bundle

# Initialize extensions
db = SQLAlchemy()

def create_app():
    # Set up file + console logging before anything else can fail, so that
    # startup problems land in logs/api.log instead of vanishing.
    logger = configure_logging()

    # Do this before anything can make an outbound HTTPS call. The frozen
    # build resolves its CA bundle into %TEMP%, which does not survive a
    # long-running service; ensure_ca_bundle() moves it somewhere that does.
    ensure_ca_bundle()

    app = Flask(__name__)
    app.config.from_object(Config)

    db.schema = app.config['SCHEMA_NAME']

    # Initialize extensions with the app
    db.init_app(app)



     #  Import all models here so they get registered before any query
    with app.app_context():
        from app import models  # <-- Make sure this file imports all model classes


    # Register blueprints
    from app.checkin.routes import checkin_bp
    from app.checkout.routes import checkout_bp
    from app.roomchange.routes import roomchange_bp
    from app.accessibilitytype.routes import accessibilitytype_bp
    from app.cancellationreason.routes import cancellationreason_bp
    from app.cardtype.routes import cardtype_bp
    from app.checkinguest.routes import checkinguest_bp
    from app.checkintype.routes import checkintype_bp
    from app.checkouttype.routes import checkouttype_bp
    from app.country.routes import country_bp
    from app.documenttype.routes import documenttype_bp
    from app.dtcmaction.routes import dtcmaction_bp
    from app.emirate.routes import emirate_bp
    from app.escorttype.routes import escorttype_bp
    from app.guest.routes import guest_bp
    from app.guestattachment.routes import guestattachment_bp
    from app.guestdocumentimage.routes import guestdocumentimage_bp
    from app.guestversion.routes import guestversion_bp
    from app.log.routes import log_bp
    from app.mainguestchange.routes import mainguestchange_bp
    from app.payment.routes import payment_bp
    from app.paymenttype.routes import paymenttype_bp
    from app.relationship.routes import relationship_bp
    from app.room.routes import room_bp
    from app.visitpurpose.routes import visitpurpose_bp
    from app.guestcheckout.routes import guestcheckout_bp
    from app.checkincancellation.routes import checkincancellation_bp
    from app.changes.routes import changes_bp


    
    

    app.register_blueprint(checkin_bp)
    app.register_blueprint(checkout_bp)
    app.register_blueprint(roomchange_bp)
    app.register_blueprint(accessibilitytype_bp)
    app.register_blueprint(cancellationreason_bp)
    app.register_blueprint(cardtype_bp)
    app.register_blueprint(checkinguest_bp)
    app.register_blueprint(checkintype_bp)
    app.register_blueprint(checkouttype_bp)
    app.register_blueprint(country_bp)
    app.register_blueprint(documenttype_bp)
    app.register_blueprint(dtcmaction_bp)
    app.register_blueprint(emirate_bp)
    app.register_blueprint(escorttype_bp)
    app.register_blueprint(guest_bp)
    app.register_blueprint(guestattachment_bp)
    app.register_blueprint(guestdocumentimage_bp)
    app.register_blueprint(guestversion_bp)
    app.register_blueprint(log_bp)
    app.register_blueprint(mainguestchange_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(paymenttype_bp)
    app.register_blueprint(relationship_bp)
    app.register_blueprint(room_bp)
    app.register_blueprint(visitpurpose_bp)
    app.register_blueprint(guestcheckout_bp)
    app.register_blueprint(checkincancellation_bp)
    app.register_blueprint(changes_bp)

    # Health checks, metrics, JSON error handlers and the /status dashboard.
    # Registered last so it can see every route above in /routes.
    from app.monitoring import init_monitoring
    init_monitoring(app)

    # gzip and ETag/304 for the table dumps. Installed after the blueprints so
    # the hook sees every response, and after init_monitoring so the request
    # log records the status the client actually got, 304 included.
    from app.utilities.http_response import init_http_response
    init_http_response(app)

    logger.info("Application created with %d routes", len(list(app.url_map.iter_rules())))
    logger.info("Database: %s", Config.safe_database_uri())

    return app