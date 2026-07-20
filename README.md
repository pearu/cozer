# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/pearu/cozer/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                          |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| cozer/\_\_init\_\_.py         |        1 |        0 |        0 |        0 |    100% |           |
| cozer/\_\_main\_\_.py         |       28 |       14 |        6 |        2 |     47% | 22, 25-47 |
| cozer/\_py2compat.py          |       30 |        0 |       14 |        0 |    100% |           |
| cozer/analyzer.py             |      630 |        7 |      372 |       24 |     96% |179-\>181, 181-\>173, 243-\>245, 245-\>298, 273-279, 284-\>286, 286-\>298, 315-\>317, 408-\>410, 410-\>402, 460-\>462, 462-\>426, 479-\>481, 510-\>426, 514-\>426, 518-\>426, 520-\>522, 522-\>426, 586-\>596, 594-\>596, 658-\>672, 661-\>672, 664-\>672, 670-\>672 |
| cozer/app/\_\_init\_\_.py     |        0 |        0 |        0 |        0 |    100% |           |
| cozer/app/classpart.py        |      333 |       28 |      100 |       23 |     86% |92, 99, 102, 106, 112, 115, 118-\>122, 120-\>122, 125, 126-\>128, 128-\>136, 132-\>135, 137, 146, 156-\>exit, 214-216, 240-242, 245, 319-320, 364-\>363, 406-413, 426-\>exit, 429, 441-\>440, 442-\>441, 449, 458-\>462 |
| cozer/app/crashreport.py      |      191 |        7 |       38 |        5 |     95% |43, 157-\>164, 160-161, 258, 262, 301-302 |
| cozer/app/editor.py           |      417 |       33 |      126 |       15 |     90% |191-195, 213-227, 289-\>exit, 291-\>exit, 296-\>exit, 301-\>exit, 397-\>394, 412, 420-426, 475, 485, 507-\>exit, 514, 524, 526, 577, 580-\>579, 588-\>590 |
| cozer/app/grids.py            |      287 |       33 |       74 |       16 |     85% |52, 82-\>89, 84-\>89, 109, 112, 142, 149, 152-\>160, 156-\>158, 161, 167, 170-173, 176-179, 194-197, 259, 262-264, 266, 273-275, 280, 314-316, 339-\>342, 344-\>351, 364-365, 387-\>exit, 401-\>exit |
| cozer/app/main.py             |      446 |       23 |      130 |       26 |     91% |105, 129-\>131, 289-\>294, 299-304, 339, 348, 360, 363, 378, 380-\>exit, 458, 460-\>exit, 469, 477, 479, 574, 578, 587-\>585, 591-\>589, 612-613, 620-\>exit, 725, 739-\>745, 741-\>743, 768, 786, 788-\>exit |
| cozer/app/ruleset.py          |       82 |        0 |       38 |        3 |     98% |124-\>123, 130-\>126, 142-\>144 |
| cozer/app/timer.py            |      417 |       19 |      116 |       17 |     93% |89-90, 100-101, 108, 112, 116, 171, 217, 350-\>exit, 371-\>exit, 429, 435-\>434, 465, 472, 478, 482, 506, 510-511, 524-\>521, 549-550, 554-\>556, 573-\>exit |
| cozer/classes.py              |       12 |        0 |        0 |        0 |    100% |           |
| cozer/phases.py               |       99 |        1 |       36 |        0 |     99% |        68 |
| cozer/qualification.py        |       83 |        0 |       32 |        0 |    100% |           |
| cozer/raceclock.py            |       38 |        4 |        8 |        2 |     83% |90, 106-108 |
| cozer/racepattern.py          |      289 |       14 |      170 |       11 |     95% |40, 73, 75, 178-179, 274, 276, 290-291, 293, 296, 299, 312, 322, 387-\>373 |
| cozer/records.py              |       60 |        0 |       20 |        2 |     98% |77-\>71, 92-\>91 |
| cozer/reports/\_\_init\_\_.py |        7 |        0 |        0 |        0 |    100% |           |
| cozer/reports/common.py       |       60 |        5 |       24 |        3 |     90% |35, 47, 50, 66-67 |
| cozer/reports/endurance.py    |       72 |        1 |       22 |        2 |     97% |38-\>40, 46 |
| cozer/reports/final.py        |      155 |        1 |       58 |        3 |     98% |57-\>55, 105, 209-\>211 |
| cozer/reports/intermediate.py |       96 |        1 |       30 |        2 |     98% |30, 126-\>103 |
| cozer/reports/labels.py       |        9 |        0 |        0 |        0 |    100% |           |
| cozer/reports/laps.py         |       53 |        1 |       14 |        1 |     97% |        24 |
| cozer/reports/latexish.py     |       74 |        4 |       44 |        4 |     93% |59, 78, 104, 114 |
| cozer/reports/letters.py      |       54 |        2 |       10 |        0 |     97% |     55-56 |
| cozer/reports/output.py       |       12 |        0 |        2 |        0 |    100% |           |
| cozer/reports/participants.py |       66 |        1 |       22 |        2 |     97% |15-\>17, 20 |
| cozer/reports/render.py       |       10 |        0 |        0 |        0 |    100% |           |
| cozer/seeding.py              |       89 |        0 |       36 |        1 |     99% | 144-\>142 |
| cozer/store.py                |      215 |        4 |       68 |        2 |     98% |243-244, 293-\>295, 327-\>exit, 330-331 |
| cozer/validate.py             |       93 |        9 |       34 |        4 |     90% |65-66, 118-\>124, 120-\>124, 126-127, 166-167, 176, 180-181, 200-\>187 |
| **TOTAL**                     | **4508** |  **212** | **1644** |  **170** | **93%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/pearu/cozer/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/pearu/cozer/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pearu/cozer/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/pearu/cozer/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fpearu%2Fcozer%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/pearu/cozer/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.