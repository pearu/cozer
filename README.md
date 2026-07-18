[![Coverage](https://raw.githubusercontent.com/pearu/cozer/python-coverage-comment-action-data/badge.svg)](https://github.com/pearu/cozer/tree/python-coverage-comment-action-data)

COZER is a program for organizing competitive events. In particular, for events of the Aquatic Motorsports according to U.I.M. Circuit Rules.

To use COZER, starting from year 2016 you'll need an user license. The license will be issued either on yearly or event basis. For more information about the pricing options, please contact Pearu Peterson <pearu.peterson@gmail.com> .

To keep COZER alive also in future, consider donating to the project.

If you have any feature requests or need support, contact Pearu for availability and pricing.

## Running COZER

COZER is launched from the command line:

    python -m cozer                       # start with an empty event
    python -m cozer event.cozj            # open an existing event (or a legacy .coz)

### Composing an event from rule sets

Rule sets — reusable definitions of a competition's scoring system, class-name
vocabulary and penalty rules — are stored as ordinary `.cozj` files (of kind
`ruleset`). Pass several files on the command line to accumulate them into a
single event:

    python -m cozer uim_general_2013.cozj uim_circuit_2013.cozj        # build a new event
    python -m cozer event.cozj uim_general_2013.cozj uim_circuit_2013.cozj   # apply to an event

- **Only rule-set files** — their scoring, class names and rules are combined
  into a new initial event.
- **One event file plus rule-set files** — the event is opened and the rule sets
  are applied *non-destructively*: any missing class names and rules are added and
  an empty scoring system is filled, but the event's own data is never overwritten.

Anything that would overwrite existing data is reported in the terminal and the
Log tab (the existing value is kept). At most one non-rule-set event file may be
given. Bundled UIM rule sets ship under `cozer/rulesets/`.

