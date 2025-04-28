# RGS Endpoints

This specification outlines the API endpoints that are available to a
provider when communicating with the Stake Engine. Through
these APIs a provider can do many functions including; create a bet,
complete a bet, validate a session and get a players balance.

# Introduction

The provider integration displays the communication between the
providers Frontend to the Stake Engine endpoints. These endpoints are used for
creating bets, getting players balances and completing bets. The core API
functionality has been thoroughly documented with requests and response
information.

# URL structure

Stake Engine will host games under a predefined URL for your team. Use this information to interact with the RGS on behalf of the user and use these parameters to display the correct information to the user.

https://games.stake-engine.com/{{.TeamID}}/{{.GameID}}/{{.GameVersion}}/index.html?sessionID={{.SessionID}}&gameID={{.GameID}}&lang={{.Lang}}&device={{.Device}}&rgs_url={{.RgsUrl}}

| Field     | Description                                                                                                                                                                                                                    |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| sessionID | Session ID is a unique session for a player, using this token within requests allows the game to make requests for the user.                                                                                                   |
| gameID    | Describes the game ID with the Stake Engine system, many API calls will require the GameID in the parameters.                                                                                                                  |
| lang      | The language the user intends to play the game in. It is up to the provider to define translations for each language if they wish their game to be played in different languages.                                              |
| device    | Either 'mobile' or 'desktop'                                                                                                                                                                                                   |
| rgs_url   | This is the url to send the subsequent request to for Authentication, making bets and completing rounds. The URL should never be hard coded as Stake Engine may dynamically change the endpoint URLs without consulting Teams. |

## Language

Language in which the player wants the game displayed in (ISO 639-1)

- https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes

Below is a list of languages within Stake.com which can be expected values.

- ar (Arabic)
- de (German)
- en (English)
- es (Spanish)
- fi (Finnish)
- fr (French)
- hi (Hindi)
- id (Indonesian)
- ja (Japanese)
- ko (Korean)
- pl (Polish)
- pt (Portuguese)
- ru (Russian)
- tr (Turkish)
- vi (Vietnamese)
- zh (Chinese)

# Understanding Money

Monetary values in the Stake Engine API are all Integer values. There are 6 decimal points of precision for all values.

- 100000 = 0.1
- 1000000 = 1
- 10000000 = 10
- 100000000 = 100

When a player wishes to place a $1 bet, you would pass in "1000000" as the value for the amount.

Currency does not affect the web development except for displaying the correct currency symbols to the player as they play.

## Currency List

- USD (United States)
- CAD (Canada)
- JPY (Japan)
- EUR (Europe)
- RUB (Ruble)
- CNY (Yuan)
- PHP (Peso)
- INR (Rupee)
- IDR (Rupiah)
- KRW (Won)
- BRL (Real)
- MXN (Peso)
- DKK (Krone)
- PLN (Polish)
- VND (Vietnamese)
- TRY (Turkish)
- CLP (Chilean)
- ARS (Argentina)
- PEN (Peru)

### Social Casino Currencies

- XGC (Gold)
- XSC (Stake Cash)

## Bet Levels

Bet levels are not enforced although there are a few rules for a valid bet amount.

1. A bet must be between the Min and the Max values returned in the `/wallet/authenticate` endpoint.
2. The bet amount must be divisible by the `stepBet` returned in the `/wallet/authenticate` endpoint.

The use of bet levels returned by `/wallet/authenticate` are recommended though to help display the correct values.

```
"minBet": 100000,
"maxBet": 1000000000,
"stepBet": 10000,
"betLevels": [
    100000, ($0.10)
    200000,
    400000,
    600000,
    800000,
    1000000,
    1200000,
    1400000,
    1600000,
    1800000,
    2000000,
    3000000,
    4000000,
    5000000,
    6000000,
    7000000,
    8000000,
    9000000,
    10000000,
    12000000,
    14000000,
    16000000,
    18000000,
    20000000,
    30000000,
    40000000,
    50000000,
    75000000,
    100000000,
    150000000,
    200000000,
    250000000,
    300000000,
    350000000,
    400000000,
    450000000,
    500000000,
    750000000,
    1000000000 ($1000)
]
```

## Bet Modes / Cost Multipliers

A game may have many bet modes which will be defined through the game config, see the math documentation for how these are defined (https://carrot-engineering.github.io/math-sdk/math_docs/gamestate_section/configuration_section/betmode_overview/).

When making a play request, pass in the base bet amount and the Bet Mode and the RGS will automatically debit the player as described below:

`Player debit amount = Base bet amount * bet mode cost multiplier`

# Wallet

The wallet endpoints interact with the RGS to make requests to the Operators Wallet API. These endpoints make interactions with an Operators Wallet API; this means any call made here will make communication to the operator about the players current session.

These endpoints are the core endpoints for the RGS.

## Authenticate Request

This endpoint validates a sessionID with the operator to ensure it is a valid session. After a session has been validated then it can be used by the other wallet endpoints below. If this endpoint is not called for a session ID; the other endpoints will throw ERR_IS for an unauthenticated session ID.

### Round

The round value on the authenticate request shows the last round this player had completed on this game. In some cases this round may still be `active`, in this case the frontend should continue displaying the round for the player.

### Request

```
POST /wallet/authenticate

{
    sessionID: "xxxxxxx",
    gameID: "xxxxxxx"
}
```

### Response

```
200
{
    balance: {
        amount: 100000,
        currency: "USD"
    }
    config: {
        gameID: "game_xxx"
        minBet: 100000,
        maxBet: 1000000000,
        stepBet: 100000,
        defaultBetLevel: 1000000,
        betLevels: [
            100000,
            200000,
            300000,
            400000,
            500000,
            600000,
            ...
        ],
        betModes: {
            BASE: {
                costMultiplier: 1,
                feature: true,
                mode: "BASE"
            },
            ANTE: {
                costMultiplier: 1.25,
                feature: true,
                mode: "ANTE"
            },
            ...
        },
        jurisdiction: {
            socialCasino: false,
            disabledFullscreen: false,
            disabledTurbo: false,
            disabledSuperTurbo: false,
            disabledAutoplay: false,
            disabledSlamstop: false,
            disabledSpacebar: false,
            disabledBuyFeature: false,
            displayNetPosition: false,
            displayRTP: false,
            displaySessionTimer: false,
            minimumRoundDuration: false
        }
    },
    round: {
        ...
    }
}
```

## Balance Request

Additional API call to receive balance of the player. Most API calls return the players balance, although a provider may want to periodically check if the balance has changed.

### Request

```
POST /wallet/balance
{
    sessionID: "xxxxxx"
}
```

### Response

```
{
    balance: {
        amount: 100000,
        currency: "USD"
    }
}
```

## Play Request

This API endpoint triggers a play where the Player is debited money to play a round of the game.

### Request

```
{
    amount: 100000,
    gameID: "xxxxxx",
    sessionID: "xxxxxxx",
    mode: "BASE"
}
```

### Response

```
{
    balance: {
        amount: 100000,
        currency: "USD"
    },
    round: {
        ...
    }
}
```

## End Round Request

This API endpoint triggers an end round to occur. No further actions can be made for this round. A payout request will be sent to the operator.

### Request

```
POST /wallet/endround
{
    sessionID: "xxxxxx",
    gameID: "xxxxxx
}
```

### Response

```
{
    balance: {
        amount: 100000,
        currency: "USD"
    },
}
```

# Game play

## Event

These endpoints are for interacting with the RGS while a round is being played. This is often used to track how much of a bet the player has observed to allow this user to continue playing a round if they disconnect. This endpoint tracks where in the bet the user is up to, send a 'event' string to this endpoint to be saved to the RGS database with the bet.

### Request

```
POST /bet/event
{
    sessionID: "xxxxxx",
    gameID: "xxxxxx",
    event: "xxxxxx"
}
```

### Response

```
{
    event: "xxxxxx"
}
```

# Response Codes

Stake Engine returns 200, 400 and 500 response codes for API requests. Below are the status code value and their meanings for the API.

## 400

All error status codes that are returned from the Stake Engine for a 400 status code.

| Status Code | Description                                              |
| ----------- | -------------------------------------------------------- |
| ERR_VAL     | Invalid Request                                          |
| ERR_IPB     | Insufficient Player Balance                              |
| ERR_IS      | Invalid Session Token / Session Timeout                  |
| ERR_ATE     | Failed User Authentication/ Authentication Token Expired |
| ERR_GLE     | Gambling limits exceeded (loss or betting)               |
| ERR_LOC     | Invalid player location for jurisdiction                 |

## 500

All error status codes that are returned from the Stake Engine for a 500 status code.

| Status Code     | Description                      |
| --------------- | -------------------------------- |
| ERR_GEN         | General Server Error             |
| ERR_MAINTENANCE | RGS is under planned maintenance |
