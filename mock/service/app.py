from flask import Flask
from time import sleep
from random import randint
import logging

## Only used to add custom spans
from opentelemetry import trace

app = Flask(__name__)

## To use without the auto-instrumentation agent: 
# from opentelemetry.instrumentation.flask import FlaskInstrumentor
# FlaskInstrumentor().instrument_app(app)

tracer = trace.get_tracer("Dice tracer")



@app.route("/")
def hello():
    logging.getLogger().warn("Time for some die rollin'!")
    return str(roll_dice() + roll_dice())


def roll_dice() -> int:
    ## A Custom sub-span beyond what is generated by the 
    ## automated instrumentation
    with tracer.start_as_current_span("roll") as rollspan:
        dice = randint(1, 6)
        rollspan.set_attribute("dice_roll", dice)
        sleep(dice / 6)
        logging.getLogger().warn(f"Wehey, we rolled a {dice}")
        return dice


if __name__ == "__main__":
    app.run(debug=True)
