from argparse import ArgumentParser
from fontmake.font_project import FontProject


def main():
    parser = ArgumentParser()
    parser.add_argument('glyphs_path', metavar='GLYPHS_PATH')
    parser.add_argument('-c', '--compatible', action='store_true')
    parser.add_argument('-i', '--interpolate', action='store_true')
    parser.add_argument('-f', '--fea-path')
    args = parser.parse_args()

    project = FontProject('src', 'out')
    project.run_all(
        args.glyphs_path, args.fea_path, args.compatible, args.interpolate)


if __name__ == '__main__':
    main()
