# JACoW Word checker constants centralized for all sections

TITLE_STYLES = {
    'normal': {
        'type': 'Paper Title',
        'styles': {
            'jacow': 'JACoW_Paper Title',
            'normal': 'Paper Title',
        },
        'alignment': 'CENTER',
        'font_size': 14.0,
        'space_before': 0.0,
        'space_after': 3.0,
        'bold': True,
        'italic': None,
    }
}
TITLE_EXTRA_RULES = [
    'Case: Title should contain greater than 70% of CAPITAL Letters, can’t be simple Title Case.',
]
TITLE_HELP_INFO = 'SCEPaperTitle'

AUTHOR_STYLES = {
    'normal': {
       'type': 'Author List',
       'styles': {
           'jacow': 'JACoW_Author List',
           'normal': 'Author List',
       },
       'alignment': 'CENTER',
       'font_size': 12.0,
       'space_before': 9.0,
       'space_after': 12.0,
       'bold': [None, False],
       'italic': [None, False],
   }
}
AUTHOR_EXTRA_RULES = ['Case: UPPER and lowercase']
AUTHOR_HELP_INFO = 'SCEAuthors'
AUTHOR_IGNORE = ['P.R. China']

ABSTRACT_STYLES = {
    'normal': {
        'type': 'Abstract Heading',
        'styles': {
            'jacow': 'JACoW_Abstract_Heading',
            'normal': 'Abstract_Heading',
        },
        'alignment': None,
        'font_size': 12.0,
        'space_before': 0.0,
        'space_after': 3.0,
        'bold': None,
        'italic': True,
    }
}
ABSTRACT_EXTRA_RULES = [
    "Text must be <b>Abstract</b>",
]
ABSTRACT_HELP_INFO = 'SCEAbsract'

HEADING_STYLES = {
    'Section': {
        'styles': {
            'jacow': 'JACoW_Section Heading',
            'normal': 'Section Heading',
        },
        'type': 'Section Heading',
        'alignment': 'CENTER',
        'font_size': 12.0,
        'space_before': 9.0,
        'space_after': 3.0,
        'bold': True,
        'italic': None,
        'case': 'UPPER CASE',
    },
    'Subsection': {
        'styles': {
            'jacow': 'JACoW_Subsection Heading',
            'normal': 'Subsection Heading',
        },
        'type': 'Subsection Heading',
        'alignment': None,
        'font_size': 12.0,
        'space_before': 6.0,
        'space_after': 3.0,
        'bold': None,
        'italic': True,
        'case': 'Initial Caps',
    },
    'Third': {
        'styles': {
            'jacow': 'JACoW_Third - Level Heading',
            'normal': 'Third - Level Heading',
        },
        'type': 'Third Level Heading',
        'alignment': None,
        'font_size': 10.0,
        'space_before': 6.0,
        'space_after': 0.0,
        'bold': True,
        'italic': None,
        'case': 'Initial Caps',
    }
}
HEADING_EXTRA_RULES = []
HEADING_HELP_INFO = 'SCEHeadings'

PARAGRAPH_STYLES = {
    'normal': {
        'styles': {
            'jacow': 'JACoW_Body Text Indent',
            'normal': 'Body Text Indent',
        },
        'alignment': 'JUSTIFY',
        'font_size': 10.0,
        'space_before': 0.0,
        'space_after': 0.0,
        'first_line_indent': 9.35  # 0.33cm
    }
}
PARAGRAPH_EXTRA_RULES = ''
PARAGRAPH_STYLE_EXCEPTIONS = ['JACoW_Bulleted List', 'JACoW_Numbered list', 'Bulleted List', 'Numbered list']
PARAGRAPH_HELP_INFO = 'SCEParag'
ALL_PARAGRAPH_HELP_INFO = 'CSEParsedDocument'
ALL_PARAGRAPH_EXTRA_INFO = {
    'title': 'Breakdown',
    'headers': '<thead><tr><th style="width:60%">Text</th><th style="width:15%">Style</th><th style="width:15%">In Table</th><th style="width:10%">JACoW Style</th> </tr></thead>',
    'columns': ['text', 'style', 'in_table', 'style_ok']
}
PARAGRAPH_SIZE_MIN = 50

FIGURE_STYLES = {
    'SingleLine': {
        'type': 'Figure - Single Line',
        'styles': {
            'jacow': 'Figure Caption',
            'normal': 'Caption',
        },
        'alignment': 'CENTER',
        'font_size': 10.0,
        'space_before': 3.0,
        'space_after': ['>=', 3.0],
        'bold': None,
        'italic': None,
    },
    'MultiLine': {
        'type': 'Figure - Multi Line',
        'styles': {
            'jacow': 'Figure Caption Multi Line',
        },
        'alignment': 'JUSTIFY',
        'font_size': 10.0,
        'space_before': 3.0,
        'space_after': ['>=', 3.0],
        'bold': None,
        'italic': None,
    }
}
VALID_FIGURE_STYLES = ['Figure Caption', 'Figure Caption Multi Line', 'Caption', 'Caption Multi Line']
FIGURE_EXTRA_RULES = [
    'Figure captions must be directly below the figure',
    'Figure must be numbered in the order they are referred to in the main text.',
    'Figure numbers must be unique and not duplicated, or skip numbers in the series.',
    'Figure Captions 1 line long must be “centred” (“Figure Caption” Style). Figure captions 2 or more lines must be “justified” (“Caption Multi Line” Style).',
    'Figure captions and figures are not to be indented.',
    'Figure captions must start with “Figure n:”.',
    'In text references to the figure if mid-sentence must be “Fig. n”, at the start of a sentence it must be “Figure n”.',
    'Figures must have a “.” On the end of the final line.',
]
FIGURE_HELP_INFO = 'CSEFigures'

TABLE_STYLES = {
    'SingleLine': {
        'type': 'Table - Single Line',
        'styles': {
            'jacow': 'Table Caption',
        },
        'alignment': 'CENTER',
        'font_size': 10.0,
        'space_before': ['>=', 3.0],
        'space_after': 3.0,
        'bold': None,
        'italic': None,
    },
    'MultiLine': {
        'type': 'Table - Multi Line',
        'styles': {
            'jacow': 'Table Caption Multi Line',
        },
        'alignment': 'JUSTIFY',
        'font_size': 10.0,
        'space_before': ['>=', 3.0],
        'space_after': 3.0,
        'bold': None,
        'italic': None,
    }
}
TABLE_EXTRA_RULES = [
    'Table captions are actually titles, this means that they are in Title Case, and don’t have a “.” At the end, well unless exceeds 2 lines',
    'The table caption is centred if 1 line (“Table Caption” Style), and Justified if 2 or more (“Table Caption Multi Line” Style).  The table caption must appear above the Table.',
    'All tables must be numbered in the order they appear in the document and not skip a number in the sequence.',
    'All tables start with “Table n:”.',
]
TABLE_HELP_INFO = 'CSETable'

REFERENCE_STYLES = {
    'LessThanNineTotal': {
        'type': 'References when ≤ 9',
        'styles': {
            'jacow': 'JACoW_References when ≤ 9',
        },
        'alignment': 'JUSTIFY',
        'font_size': 9.0,
        'space_before': 0.0,
        'space_after': 3.0,
        'first_line_indent': -14.75,
    },
    'LessThanNine': {
        'type': 'Reference #1-9 when >= 10 Refs',
        'styles': {
            'jacow': 'JACoW_Reference #1-9 when >= 10 Refs',
        },
        'alignment': 'JUSTIFY',
        'font_size': 9.0,
        'space_before': 0.0,
        'space_after': 3.0,
        'first_line_indent': -14.75,
    },
    'MoreThanNine': {
        'type': 'Reference #10 onwards',
        'styles': {
            'jacow': 'JACoW_Reference #10 onwards',
        },
        'alignment': 'JUSTIFY',
        'font_size': 9.0,
        'space_before': 0.0,
        'space_after': 3.0,
        'first_line_indent': -19.3,
    }
}
REFERENCE_EXTRA_RULES = [
    'All references must be ordered in the reference list based on when they first are referred to in the main text.',
    'References in the main text can be [n], or [n1, n2, n5, etc.], or [n – n3].',
    'A reference can be referred to multiple times in the main text as required..',
    'All references in the reference list must be sited in the main text at least once.',
    'Reference lists which have 9 or less references must be “JACoW_Reference when <= 9 Refs” Style.',
    'When greater than 9 references the first 9 must be “JACoW_Reference #1-9 when >= 10 Refs” Style, '
    'and 10 and onwards must be “JACoW_Reference #10 onwards” Style.',
    'All references must be numbered [n] and have a tab between the ] and the start of the reference text. '
    '(note many authors put spaces in which stuffs up the spacing.',
    'DOIs and URLs should be font 8pt Liberation Mono',
]
REFERENCE_HELP_INFO = 'SCEReferences'
REFERENCE_EXTRA_INFO = {
    'title': 'Reference Breakdown',
    'headers': '<thead><tr><th>Ref</th><th>Order Ok</th><th>Style Ok</th><th>Text</th><th>In-text</th></tr></thead>',
    'columns': ['ref', 'order_ok', 'style_ok', 'text', 'in_text']
}
