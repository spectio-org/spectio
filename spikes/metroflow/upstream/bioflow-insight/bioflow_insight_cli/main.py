import click

import src as bioflow_insight_src
from src.workflow import Workflow
from src.bioflowinsighterror import BioFlowInsightError

import sys

sys.setrecursionlimit(5000)


@click.command()
@click.version_option(bioflow_insight_src.__version__)
@click.argument('main_workflow_path')
@click.option(
    '--output-dir',
    default='./results',
    help='Where the results will be written.',
)
@click.option(
    '--no-render-graphs',
    'render_graphs',
    required=False,
    default=True,
    is_flag=True,
    help='Don\'t generate the graphs output in png format using graphviz (faster),'
    'the mermaid and dot formats are always generated.',
)
@click.option(
    '--analysis',
    'analysis',
    type=click.STRING,
    required=False,
    help='todo',
    default='bioflow',
)
@click.option(
    '--name',
    'name',
    required=False,
    help='Workflow name, extracted otherwise (in the case of a Git repo).',
)
@click.option(
    '--is_workflow',
    'is_workflow',
    required=False,
    default=True,
    help='This is if you want to analyse the workflow (True) or just obtain the metro-map for a json file (False)',
)
@click.option(
    '--display-info',
    'display_info',
    required=False,
    default=True,
    is_flag=True,
    help='Option to show a visual summary of the analysis.',
)
def cli_command(main_workflow_path, **kwargs):
    return cli(main_workflow_path, **kwargs)


def cli(main_workflow_path, render_graphs: bool, **kwargs):
    """
    The path to main file, subworkflows and modules must be in direct subdir of this file,
    in folders with eponymous names.
    """
    try:
        analysis = kwargs["analysis"]
        kwargs.pop("analysis")
    except:
        analysis = "bioflow"
    try:
        is_workflow = kwargs["is_workflow"]
    except:
        is_workflow = True
    # Removing duplicate
    try:
        kwargs.pop("duplicate")
    except:
        None

    def run_metro_map_generation(w):
        w.get_metro_map_json(render_dot=True)
        try:
            w.get_metro_map_json(type_metro="condition")
        except:
            None
        try:
            w.get_metro_map_json(type_metro="dominator")
        except:
            None
        try:
            w.get_metro_map_json(type_metro="parallel")
        except:
            None

    # print(f"ANALYSIS IS DONE WITH '{analysis}'")
    if is_workflow:
        # print(analysis)
        if analysis == "bioflow":
            w = Workflow(file=main_workflow_path, **kwargs)
            w.initialise_with_bioflow()
            try:
                w.generate_specification_graph()
                w.get_metadata_specification_graph()
            except:
                None
            w.generate_process_dependency_graph()
            w.get_metadata_process_dependency_graph()

            # run_metro_map_generation(w)
            try:
                w.get_rocrate()
            except:
                None

        elif analysis == "metroflow":
            error_caught_by_nls = ""
            run_bioflow = False
            try:
                w = Workflow(file=main_workflow_path, **kwargs)
                w.initialise_with_language_server()
                run_metro_map_generation(w)
            except BioFlowInsightError as E:
                print(f"THE ERROR CAUGHT BY LANGUAGE SERVER IS {str(E)}")
                error_caught_by_nls = str(E)
                run_bioflow = True
            except:
                run_bioflow = True

            def throw_error(error_caught_by_nls):
                generic_error = "The Nextflow Language Server has detected an error in the workflow. Trying opening it with VSCode with the Nextflow plugin to fix it."
                if error_caught_by_nls == "":
                    raise Exception(generic_error)
                raise Exception(error_caught_by_nls)

            if run_bioflow:
                del w
                try:
                    w = Workflow(file=main_workflow_path, **kwargs)
                    w.initialise_with_bioflow()
                    run_metro_map_generation(w)

                except BioFlowInsightError as e:
                    print(f"THE ERROR CAUGHT BY BIOFLOW IS {str(e)}")
                    throw_error(error_caught_by_nls)
                except:
                    throw_error(error_caught_by_nls)

            # try:
            #    w = Workflow(file=main_workflow_path, **kwargs)
            #    w.initialise()
            #    w.get_metro_map_json(render_dot=True)
            # except BioFlowInsightError as e:
            #    print(f"THE ERROR CAUGHT BY BIOFLOW IS {str(e)}")
            #    raise Exception(generic_error)
            # except:
            #    print("here")
            #    raise Exception(generic_error)
        else:
            raise Exception('Unvalid value for "analysis" parameter. Either "bioflow-insight" or "metroflow"')
    else:
        w = Workflow(file=main_workflow_path, **kwargs)
        w.generate_metro_map_from_json()


if __name__ == '__main__':
    cli_command()
