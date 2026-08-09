# Credit Risk AI - Project Rules

## Python

- Python >= 3.11
- Follow PEP8
- Maximum line length: 88 characters
- Use Black formatting

---

## Naming Convention

### Classes

PascalCase

Example:

RandomForestModel
DiceExplainer

### Functions

snake_case

Example:

train_model()
predict()

### Variables

snake_case

Example:

feature_names
train_data

### Constants

UPPER_CASE

Example:

RANDOM_STATE = 42

---

## Documentation

Every class should have a docstring.

Example

"""
Random Forest Model

Handles training, prediction and saving.
"""

Every public function should have a docstring.

---

## Type Hints

Always use type hints.

Example

def train(
    self,
    X: pd.DataFrame,
    y: pd.Series
) -> None:

---

## Error Handling

Never use bare except.

Good:

except ValueError as e:

Bad:

except:

---

## Logging

Use logging instead of print.

Example:

logger.info("Training Started")

---

## Saving Models

Save all trained models inside

models/

Never save inside src/

---

## Random State

Always use

RANDOM_STATE = 42

---

## Explainability

Every explainer must inherit

BaseExplainer

---

## Model Classes

Every ML model must inherit

BaseModel

---

## Code Quality

Avoid duplicate code.

Prefer composition over duplication.

Functions should do one thing only.

---

## Folder Structure

Follow the existing project structure.

Do not create new folders unless necessary.

---

## Testing

Every module should be tested before moving to the next one.