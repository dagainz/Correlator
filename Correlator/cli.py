import argparse
import os


class BaseCLI:
    """Stuff common to several CLI utilities"""

    @staticmethod
    def _offset_spec(value: str):

        """Argparse 'type' method to handle a single integer or range in the format integer-integer

        Returns a 2 element integer list: [ start, end ]

        If a single offset is provided, both elements are set to the same integer i.e.:
            "2-3" returns [2,3]
            "5" returns [5,5]

        """

        try:
            int_value = int(value)
            return int_value, int_value
        except ValueError:
            ints = value.split('-')
            if len(ints) == 2:
                try:
                    start = int(ints[0])
                    end = int(ints[1])
                    if end >= start:
                        return start, end
                except ValueError:
                    pass
        raise TypeError('Invalid number or range')

    @staticmethod
    def _handle_configfile_argument(parser: argparse.ArgumentParser):
        """Add --config_file argument to a parser

         If the environment variable CORRELATOR_CFG exists, it will be used as the default for the
         argument, and make it non required.

         This has the effect of allowing the environment variable to set the value, allowing overriding
         with a command line option.

         """

        if 'CORRELATOR_CFG' in os.environ:
            parser.add_argument(
                '--config_file',
                default=os.environ['CORRELATOR_CFG'],
                help='Correlator configuration file'
            )
        else:
            parser.add_argument(
                '--config_file',
                required=True,
                help='Correlator configuration file'
            )
